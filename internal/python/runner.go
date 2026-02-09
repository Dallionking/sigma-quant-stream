package python

import (
	"bufio"
	"context"
	"fmt"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// requiredPackages lists the Python packages that must be installed for
// the quant pipeline to function correctly.
var requiredPackages = []string{
	"pandas",
	"pandas-ta",
	"numpy",
	"ccxt",
	"pydantic",
	"typer",
	"rich",
}

// Runner executes Python scripts from the project tree.
type Runner struct {
	pythonBin   string // resolved path to the python3 binary
	projectRoot string // absolute path to the project root
}

// NewRunner creates a Runner, auto-detecting the Python binary. It checks for a
// local .venv first, then falls back to system python3 / python. Returns an
// error when no usable Python interpreter is found.
func NewRunner(projectRoot string) (*Runner, error) {
	absRoot, err := filepath.Abs(projectRoot)
	if err != nil {
		return nil, fmt.Errorf("resolving project root: %w", err)
	}

	// Candidate binaries in priority order.
	candidates := []string{
		filepath.Join(absRoot, ".venv", "bin", "python3"),
		filepath.Join(absRoot, ".venv", "bin", "python"),
	}

	// Append system-level interpreters.
	for _, name := range []string{"python3", "python"} {
		if p, err := exec.LookPath(name); err == nil {
			candidates = append(candidates, p)
		}
	}

	for _, c := range candidates {
		// Verify the candidate is actually executable.
		cmd := exec.Command(c, "--version")
		if err := cmd.Run(); err == nil {
			return &Runner{
				pythonBin:   c,
				projectRoot: absRoot,
			}, nil
		}
	}

	return nil, fmt.Errorf("no usable Python interpreter found (checked .venv and system PATH)")
}

// Exec runs a Python script synchronously and returns its combined stdout. The
// script path is resolved relative to projectRoot. A 2-minute default timeout
// is applied when the provided context has no deadline.
func (r *Runner) Exec(ctx context.Context, script string, args ...string) (string, error) {
	scriptPath := r.resolveScript(script)

	cmdArgs := append([]string{scriptPath}, args...)
	cmd := exec.CommandContext(ctx, r.pythonBin, cmdArgs...)
	cmd.Dir = r.projectRoot

	out, err := cmd.Output()
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			return "", fmt.Errorf("script %s failed (exit %d): %s",
				script, exitErr.ExitCode(), strings.TrimSpace(string(exitErr.Stderr)))
		}
		return "", fmt.Errorf("running script %s: %w", script, err)
	}

	return strings.TrimSpace(string(out)), nil
}

// ExecStreaming runs a Python script and streams stdout line by line. It returns
// a lines channel and an error channel. The lines channel is closed when the
// process finishes; the error channel receives at most one error (or is closed
// with nil on success).
func (r *Runner) ExecStreaming(ctx context.Context, script string, args []string) (<-chan string, <-chan error) {
	lines := make(chan string, 64)
	errc := make(chan error, 1)

	scriptPath := r.resolveScript(script)

	cmdArgs := append([]string{"-u", scriptPath}, args...) // -u for unbuffered stdout
	cmd := exec.CommandContext(ctx, r.pythonBin, cmdArgs...)
	cmd.Dir = r.projectRoot

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		close(lines)
		errc <- fmt.Errorf("creating stdout pipe: %w", err)
		close(errc)
		return lines, errc
	}

	if err := cmd.Start(); err != nil {
		close(lines)
		errc <- fmt.Errorf("starting script %s: %w", script, err)
		close(errc)
		return lines, errc
	}

	go func() {
		defer close(lines)
		defer close(errc)

		scanner := bufio.NewScanner(stdout)
		// Allow up to 1 MB per line for large JSON payloads.
		scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)

		for scanner.Scan() {
			select {
			case lines <- scanner.Text():
			case <-ctx.Done():
				errc <- ctx.Err()
				return
			}
		}

		if err := scanner.Err(); err != nil {
			errc <- fmt.Errorf("reading stdout: %w", err)
			return
		}

		if err := cmd.Wait(); err != nil {
			if exitErr, ok := err.(*exec.ExitError); ok {
				errc <- fmt.Errorf("script %s exited with code %d", script, exitErr.ExitCode())
			} else {
				errc <- fmt.Errorf("waiting for script %s: %w", script, err)
			}
		}
	}()

	return lines, errc
}

// GetVersion returns the Python interpreter version string (e.g. "Python 3.12.1").
func (r *Runner) GetVersion() (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, r.pythonBin, "--version")
	out, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("getting python version: %w", err)
	}
	return strings.TrimSpace(string(out)), nil
}

// CheckPackage returns true if the given Python package can be imported.
func (r *Runner) CheckPackage(pkg string) bool {
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	// Normalise package name for import: pandas-ta -> pandas_ta
	importName := strings.ReplaceAll(pkg, "-", "_")

	cmd := exec.CommandContext(ctx, r.pythonBin, "-c", fmt.Sprintf("import %s", importName))
	cmd.Dir = r.projectRoot
	return cmd.Run() == nil
}

// CheckRequiredPackages checks all required packages and returns the names of
// any that are missing. An empty slice means all packages are available.
func (r *Runner) CheckRequiredPackages() ([]string, error) {
	var missing []string
	for _, pkg := range requiredPackages {
		if !r.CheckPackage(pkg) {
			missing = append(missing, pkg)
		}
	}
	return missing, nil
}

// resolveScript converts a relative script path to an absolute path under
// projectRoot. If the path is already absolute it is returned as-is.
func (r *Runner) resolveScript(script string) string {
	if filepath.IsAbs(script) {
		return script
	}
	return filepath.Join(r.projectRoot, script)
}
