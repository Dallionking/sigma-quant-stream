package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var (
	cfgFile string
	verbose bool
	noColor bool
)

var rootCmd = &cobra.Command{
	Use:   "sigma-quant",
	Short: "Autonomous strategy research factory",
	Long: `Sigma-Quant Stream — Your Autonomous Strategy Research Team

A swarm of AI agents that discover, backtest, and validate
trading strategies for futures and crypto markets.`,
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("Sigma-Quant Stream v1.0.0")
		fmt.Println("Run 'sigma-quant --help' for available commands")
	},
}

func Execute() error {
	return rootCmd.Execute()
}

func init() {
	cobra.OnInitialize(initConfig)
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is ./config.json)")
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "verbose output")
	rootCmd.PersistentFlags().BoolVar(&noColor, "no-color", false, "disable color output")
}

func initConfig() {
	if cfgFile != "" {
		viper.SetConfigFile(cfgFile)
	} else {
		viper.SetConfigName("config")
		viper.SetConfigType("json")
		viper.AddConfigPath(".")
	}
	viper.AutomaticEnv()
	_ = viper.ReadInConfig()
}
