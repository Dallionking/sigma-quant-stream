package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/Dallionking/sigma-quant-stream/internal/config"
	"github.com/Dallionking/sigma-quant-stream/internal/tui/styles"
	"github.com/spf13/cobra"
)

// --- data (parent) ---

var dataCmd = &cobra.Command{
	Use:   "data",
	Short: "Data management commands",
	Long: `Manage market data for strategy research.

Subcommands:
  download   Download historical market data
  status     Show data coverage and freshness`,
	RunE: func(cmd *cobra.Command, args []string) error {
		return cmd.Help()
	},
}

// --- data download ---

var (
	dataDownloadMarket  string
	dataDownloadSymbols string
	dataDownloadPeriod  string
)

var dataDownloadCmd = &cobra.Command{
	Use:   "download",
	Short: "Download historical market data",
	Long: `Download historical OHLCV data for strategy backtesting.

Data is stored in the project's data/ directory, organised by
market type and symbol.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		root, err := config.DetectProjectRoot()
		if err != nil {
			return fmt.Errorf("detecting project root: %w", err)
		}

		if _, err := config.Load(root); err != nil {
			return fmt.Errorf("loading config: %w", err)
		}

		fmt.Println(styles.Title.Render("Data Download"))
		fmt.Println()

		fmt.Println(styles.Label.Render("MARKET") + "   " + styles.Value.Render(dataDownloadMarket))
		fmt.Println(styles.Label.Render("SYMBOLS") + "  " + styles.Value.Render(dataDownloadSymbols))
		fmt.Println(styles.Label.Render("PERIOD") + "   " + styles.Value.Render(dataDownloadPeriod))
		fmt.Println()

		// TODO: Wire to python.DownloadData when streaming progress is ready.
		// runner, err := python.NewRunner(root)
		// progress, err := runner.DownloadData(ctx, python.DownloadOptions{
		//     Market:  dataDownloadMarket,
		//     Symbols: strings.Split(dataDownloadSymbols, ","),
		//     Period:  dataDownloadPeriod,
		// })

		fmt.Println(styles.Dim("Data download placeholder -- will invoke python.DownloadData with streaming progress"))

		return nil
	},
}

// --- data status ---

var dataStatusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show data coverage and freshness",
	Long:  `Display the current state of downloaded market data, including file sizes, date ranges, and staleness.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		root, err := config.DetectProjectRoot()
		if err != nil {
			return fmt.Errorf("detecting project root: %w", err)
		}

		if _, err := config.Load(root); err != nil {
			return fmt.Errorf("loading config: %w", err)
		}

		paths := config.NewPaths(root)
		dataDir := paths.Data

		fmt.Println(styles.Title.Render("Data Status"))
		fmt.Println()
		fmt.Println(styles.Label.Render("DATA DIR") + "  " + styles.Value.Render(dataDir))
		fmt.Println()

		// Scan data directory for files.
		entries, err := os.ReadDir(dataDir)
		if err != nil {
			if os.IsNotExist(err) {
				fmt.Println(styles.Dim("  No data directory found. Run 'sigma-quant data download' first."))
				return nil
			}
			return fmt.Errorf("reading data directory: %w", err)
		}

		if len(entries) == 0 {
			fmt.Println(styles.Dim("  Data directory is empty. Run 'sigma-quant data download' first."))
			return nil
		}

		fmt.Printf("  %s  %s  %s\n",
			styles.TableHeader.Width(30).Render("FILE"),
			styles.TableHeader.Width(12).Render("SIZE"),
			styles.TableHeader.Width(20).Render("MODIFIED"),
		)
		fmt.Println(styles.Divider(64))

		for i, e := range entries {
			info, err := e.Info()
			if err != nil {
				continue
			}

			row := styles.TableRow(i%2 == 0)
			name := styles.TruncateWithEllipsis(e.Name(), 28)
			size := formatFileSize(info.Size())
			modified := info.ModTime().Format("2006-01-02 15:04")

			fmt.Printf("  %s  %s  %s\n",
				row.Width(30).Render(name),
				styles.Dim(fmt.Sprintf("%12s", size)),
				styles.Dim(modified),
			)
		}

		fmt.Println()

		// Count total files recursively.
		totalFiles := 0
		var totalSize int64
		_ = filepath.Walk(dataDir, func(_ string, info os.FileInfo, err error) error {
			if err != nil {
				return nil
			}
			if !info.IsDir() {
				totalFiles++
				totalSize += info.Size()
			}
			return nil
		})

		fmt.Printf("  %s files, %s total\n",
			styles.Value.Render(fmt.Sprintf("%d", totalFiles)),
			styles.Value.Render(formatFileSize(totalSize)),
		)

		return nil
	},
}

// formatFileSize returns a human-readable file size string.
func formatFileSize(bytes int64) string {
	const (
		kb = 1024
		mb = 1024 * kb
		gb = 1024 * mb
	)

	switch {
	case bytes >= gb:
		return fmt.Sprintf("%.1f GB", float64(bytes)/float64(gb))
	case bytes >= mb:
		return fmt.Sprintf("%.1f MB", float64(bytes)/float64(mb))
	case bytes >= kb:
		return fmt.Sprintf("%.1f KB", float64(bytes)/float64(kb))
	default:
		return fmt.Sprintf("%d B", bytes)
	}
}

func init() {
	dataDownloadCmd.Flags().StringVar(&dataDownloadMarket, "market", "futures", "market type: futures, crypto-cex, or crypto-dex")
	dataDownloadCmd.Flags().StringVar(&dataDownloadSymbols, "symbols", "", "comma-separated symbols (e.g. ES,NQ or BTC/USDT)")
	dataDownloadCmd.Flags().StringVar(&dataDownloadPeriod, "period", "2y", "historical period: 2y, 5y, 15y")

	dataCmd.AddCommand(dataDownloadCmd)
	dataCmd.AddCommand(dataStatusCmd)
	rootCmd.AddCommand(dataCmd)
}
