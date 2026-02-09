package health

import (
	"context"
	"time"
)

// Status represents the result of a single health check.
type Status int

const (
	StatusPass Status = iota
	StatusWarn
	StatusFail
)

// String returns the lowercase text representation of the status.
func (s Status) String() string {
	switch s {
	case StatusPass:
		return "pass"
	case StatusWarn:
		return "warn"
	case StatusFail:
		return "fail"
	default:
		return "unknown"
	}
}

// Symbol returns the display symbol for the status.
func (s Status) Symbol() string {
	switch s {
	case StatusPass:
		return "+"
	case StatusWarn:
		return "!"
	case StatusFail:
		return "x"
	default:
		return "?"
	}
}

// CheckResult holds the result of a single check.
type CheckResult struct {
	Name     string
	Category string // "system", "project", "data", "runtime"
	Status   Status
	Message  string
	Duration time.Duration
}

// Report holds results of all checks.
type Report struct {
	Results  []CheckResult
	Passed   int
	Warned   int
	Failed   int
	Total    int
	Duration time.Duration
	Healthy  bool
}

// Check is a named, categorized health check function.
type Check struct {
	Name     string
	Category string
	Fn       func(ctx context.Context) CheckResult
}

// Checker runs all registered health checks against a project root.
type Checker struct {
	checks      []Check
	projectRoot string
}

// NewChecker creates a health checker for the given project root.
func NewChecker(projectRoot string) *Checker {
	c := &Checker{
		projectRoot: projectRoot,
	}
	c.registerChecks()
	return c
}

// add registers a single check.
func (c *Checker) add(name, category string, fn func(ctx context.Context) CheckResult) {
	c.checks = append(c.checks, Check{
		Name:     name,
		Category: category,
		Fn:       fn,
	})
}

// RunAll runs every registered check and returns a report.
func (c *Checker) RunAll(ctx context.Context) *Report {
	start := time.Now()
	results := make([]CheckResult, 0, len(c.checks))

	for _, ch := range c.checks {
		if ctx.Err() != nil {
			results = append(results, CheckResult{
				Name:     ch.Name,
				Category: ch.Category,
				Status:   StatusFail,
				Message:  "context cancelled",
			})
			continue
		}
		t := time.Now()
		r := ch.Fn(ctx)
		r.Duration = time.Since(t)
		r.Name = ch.Name
		r.Category = ch.Category
		results = append(results, r)
	}

	return buildReport(results, time.Since(start))
}

// RunCategory runs only the checks matching the given category.
func (c *Checker) RunCategory(ctx context.Context, category string) *Report {
	start := time.Now()
	var results []CheckResult

	for _, ch := range c.checks {
		if ch.Category != category {
			continue
		}
		if ctx.Err() != nil {
			results = append(results, CheckResult{
				Name:     ch.Name,
				Category: ch.Category,
				Status:   StatusFail,
				Message:  "context cancelled",
			})
			continue
		}
		t := time.Now()
		r := ch.Fn(ctx)
		r.Duration = time.Since(t)
		r.Name = ch.Name
		r.Category = ch.Category
		results = append(results, r)
	}

	return buildReport(results, time.Since(start))
}

// buildReport aggregates a slice of results into a Report.
func buildReport(results []CheckResult, dur time.Duration) *Report {
	r := &Report{
		Results:  results,
		Total:    len(results),
		Duration: dur,
	}
	for _, res := range results {
		switch res.Status {
		case StatusPass:
			r.Passed++
		case StatusWarn:
			r.Warned++
		case StatusFail:
			r.Failed++
		}
	}
	r.Healthy = r.Failed == 0
	return r
}
