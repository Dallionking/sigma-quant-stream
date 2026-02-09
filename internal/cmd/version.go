package cmd

import (
	"fmt"
	"runtime"

	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
	"github.com/spf13/cobra"
)

// Build-time variables set via ldflags.
var (
	Version   = "dev"
	GitCommit = "none"
	BuildDate = "unknown"
)

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print version information",
	Long:  `Display the build version, git commit, build date, and Go runtime details.`,
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println(styles.Cyan(styles.CompactLogo) + "  " + styles.Value.Render("v"+Version))
		fmt.Println()
		fmt.Println(styles.Label.Render("VERSION") + "   " + styles.Value.Render(Version))
		fmt.Println(styles.Label.Render("COMMIT") + "    " + styles.Value.Render(GitCommit))
		fmt.Println(styles.Label.Render("BUILT") + "     " + styles.Value.Render(BuildDate))
		fmt.Println(styles.Label.Render("GO") + "        " + styles.Value.Render(runtime.Version()))
		fmt.Println(styles.Label.Render("OS/ARCH") + "   " + styles.Value.Render(runtime.GOOS+"/"+runtime.GOARCH))
	},
}

func init() {
	rootCmd.AddCommand(versionCmd)
}
