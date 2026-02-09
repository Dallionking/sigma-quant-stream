package cmd

import (
	"fmt"

	"github.com/Dallionking/sigma-quant-stream/internal/config"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
	"github.com/spf13/cobra"
)

// --- config (parent) ---

var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Configuration management",
	Long: `View and manage Sigma-Quant Stream configuration.

When run without subcommands, displays the current configuration summary.

Subcommands:
  profiles   List available market profiles
  switch     Switch the active market profile`,
	RunE: func(cmd *cobra.Command, args []string) error {
		root, err := config.DetectProjectRoot()
		if err != nil {
			return fmt.Errorf("detecting project root: %w", err)
		}

		cfg, err := config.Load(root)
		if err != nil {
			return fmt.Errorf("loading config: %w", err)
		}

		fmt.Println(styles.Title.Render("Configuration"))
		fmt.Println()

		fmt.Println(styles.Label.Render("NAME") + "      " + styles.Value.Render(cfg.Name))
		fmt.Println(styles.Label.Render("VERSION") + "   " + styles.Value.Render(cfg.Version))
		fmt.Println(styles.Label.Render("PROFILE") + "   " + styles.Value.Render(cfg.ActiveProfile))
		fmt.Println(styles.Label.Render("MODE") + "      " + styles.Value.Render(cfg.Defaults.Mode))
		fmt.Println(styles.Label.Render("PANES") + "     " + styles.Value.Render(fmt.Sprintf("%d", cfg.Defaults.Panes)))
		fmt.Println(styles.Label.Render("ROOT") + "      " + styles.Value.Render(root))
		fmt.Println()

		fmt.Println(styles.Divider(50))
		fmt.Println()

		// Workers.
		fmt.Println(styles.Subtitle.Render("Workers"))
		fmt.Println(styles.Label.Render("  COUNT") + "   " + styles.Value.Render(fmt.Sprintf("%d", cfg.Workers.Count)))
		for _, wt := range cfg.Workers.Types {
			fmt.Println("  " + styles.Dim("-") + " " + styles.Bold(wt))
		}
		fmt.Println()

		// Modes.
		fmt.Println(styles.Subtitle.Render("Modes"))
		for name, mode := range cfg.Modes {
			active := ""
			if name == cfg.Defaults.Mode {
				active = " " + styles.Cyan("(active)")
			}
			fmt.Printf("  %s%s  timeout=%ds budget=$%.0f source=%s\n",
				styles.Bold(name), active,
				mode.SessionTimeout, mode.BudgetCap, mode.DataSource,
			)
		}
		fmt.Println()

		// Profiles.
		fmt.Println(styles.Subtitle.Render("Market Profiles"))
		for name, ref := range cfg.MarketProfiles {
			active := ""
			if ref.Path == cfg.ActiveProfile {
				active = " " + styles.Cyan("(active)")
			}
			fmt.Printf("  %s%s  %s  %s\n",
				styles.Bold(name), active,
				styles.Dim(ref.MarketType),
				styles.Dim(ref.Path),
			)
		}

		return nil
	},
}

// --- config profiles ---

var configProfilesCmd = &cobra.Command{
	Use:   "profiles",
	Short: "List available market profiles",
	RunE: func(cmd *cobra.Command, args []string) error {
		root, err := config.DetectProjectRoot()
		if err != nil {
			return fmt.Errorf("detecting project root: %w", err)
		}

		cfg, err := config.Load(root)
		if err != nil {
			return fmt.Errorf("loading config: %w", err)
		}

		fmt.Println(styles.Title.Render("Market Profiles"))
		fmt.Println()

		profiles, err := config.ListProfiles()
		if err != nil {
			return fmt.Errorf("listing profiles: %w", err)
		}

		if len(profiles) == 0 {
			fmt.Println(styles.Dim("  No profiles configured in config.json"))
			return nil
		}

		fmt.Printf("  %s  %s  %s  %s\n",
			styles.TableHeader.Width(16).Render("NAME"),
			styles.TableHeader.Width(14).Render("MARKET TYPE"),
			styles.TableHeader.Width(20).Render("DISPLAY NAME"),
			styles.TableHeader.Width(30).Render("PATH"),
		)
		fmt.Println(styles.Divider(82))

		i := 0
		for name, ref := range cfg.MarketProfiles {
			row := styles.TableRow(i%2 == 0)
			active := ""
			if ref.Path == cfg.ActiveProfile {
				active = " " + styles.Cyan("*")
			}

			fmt.Printf("  %s%s  %s  %s  %s\n",
				row.Width(16).Render(name),
				active,
				styles.Dim(fmt.Sprintf("%-14s", ref.MarketType)),
				styles.Dim(fmt.Sprintf("%-20s", ref.DisplayName)),
				styles.Dim(styles.TruncateWithEllipsis(ref.Path, 28)),
			)
			i++
		}

		fmt.Println()
		fmt.Println(styles.Dim("  * = active profile"))

		return nil
	},
}

// --- config switch ---

var configSwitchCmd = &cobra.Command{
	Use:   "switch <profile>",
	Short: "Switch the active market profile",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		profileName := args[0]

		root, err := config.DetectProjectRoot()
		if err != nil {
			return fmt.Errorf("detecting project root: %w", err)
		}

		if _, err := config.Load(root); err != nil {
			return fmt.Errorf("loading config: %w", err)
		}

		if err := config.SwitchProfile(profileName); err != nil {
			return fmt.Errorf("switching profile: %w", err)
		}

		fmt.Println(styles.Green("Switched active profile to") + " " + styles.Value.Render(profileName))

		return nil
	},
}

func init() {
	configCmd.AddCommand(configProfilesCmd)
	configCmd.AddCommand(configSwitchCmd)
	rootCmd.AddCommand(configCmd)
}
