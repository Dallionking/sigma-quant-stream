#!/usr/bin/env node
/**
 * iTerm2 Quant Team Launcher
 * ==========================
 * Creates a 6-pane iTerm2 layout for the Quant Research Team.
 * Each pane runs a Claude Code instance with a specific worker role.
 *
 * Layout:
 * ┌──────────────┬──────────────┬──────────────┐
 * │    Pane 1    │    Pane 2    │    Pane 3    │
 * │  researcher  │  converter   │  backtester  │
 * ├──────────────┼──────────────┼──────────────┤
 * │    Pane 4    │    Pane 5    │    Pane 6    │
 * │  optimizer   │  validator   │  distiller   │
 * └──────────────┴──────────────┴──────────────┘
 *
 * Usage: node iterm-quant-launcher.js [preset] [maxIterations]
 * Presets: balanced, research_heavy, backtest_heavy, full_cycle
 */

const { execFileSync, spawnSync, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// Configuration
const PROJECT_ROOT = path.resolve(__dirname, '..');
const QUANT_WORKTREE = PROJECT_ROOT;  // Standalone project — worktree IS project root
const STREAM_QUANT = PROJECT_ROOT;
const SCRIPTS_DIR = path.join(PROJECT_ROOT, 'scripts/quant-team');
const PROMPTS_DIR = path.join(PROJECT_ROOT, 'prompts');

/**
 * Sleep helper - returns a promise that resolves after ms milliseconds
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Run osascript with an array of lines
 */
function osascript(lines) {
  const script = lines.join('\n');
  try {
    execSync(`osascript -e '${script.replace(/'/g, "'\"'\"'")}'`, { stdio: 'pipe' });
    return true;
  } catch (error) {
    console.error('AppleScript error:', error.message);
    return false;
  }
}

/**
 * Send text to a specific iTerm2 session by index
 * Sessions are numbered starting at 1
 */
function sendToSession(sessionIndex, text) {
  // Escape special characters for AppleScript
  const escapedText = text
    .replace(/\\/g, '\\\\')
    .replace(/"/g, '\\"')
    .replace(/\n/g, '\\n');

  const script = [
    'tell application "iTerm"',
    '  tell current window',
    '    tell current tab',
    `      tell session ${sessionIndex}`,
    `        write text "${escapedText}"`,
    '      end tell',
    '    end tell',
    '  end tell',
    'end tell',
  ];

  return osascript(script);
}

/**
 * Escape special characters for AppleScript string interpolation
 * Prevents injection when worker names or paths contain quotes/backslashes
 */
function escapeAppleScript(str) {
  return str
    .replace(/\\/g, '\\\\')  // Escape backslashes first
    .replace(/"/g, '\\"');   // Escape double quotes
}

// Worker assignments (default: balanced preset)
const WORKER_ASSIGNMENTS = {
  balanced: [
    { pane: 1, worker: 'researcher' },
    { pane: 2, worker: 'converter' },
    { pane: 3, worker: 'backtester' },
    { pane: 4, worker: 'optimizer' },
    { pane: 5, worker: 'prop_firm_validator' },
    { pane: 6, worker: 'knowledge_distiller' },
  ],
  research_heavy: [
    { pane: 1, worker: 'researcher' },
    { pane: 2, worker: 'researcher' },
    { pane: 3, worker: 'converter' },
    { pane: 4, worker: 'backtester' },
    { pane: 5, worker: 'optimizer' },
    { pane: 6, worker: 'prop_firm_validator' },
  ],
  backtest_heavy: [
    { pane: 1, worker: 'researcher' },
    { pane: 2, worker: 'backtester' },
    { pane: 3, worker: 'backtester' },
    { pane: 4, worker: 'optimizer' },
    { pane: 5, worker: 'optimizer' },
    { pane: 6, worker: 'prop_firm_validator' },
  ],
  full_cycle: [
    { pane: 1, worker: 'researcher' },
    { pane: 2, worker: 'converter' },
    { pane: 3, worker: 'backtester' },
    { pane: 4, worker: 'backtester' },
    { pane: 5, worker: 'optimizer' },
    { pane: 6, worker: 'prop_firm_validator' },
  ],
};

/**
 * Generate the worker prompt for a specific pane
 * Reads the worker markdown and adds task context
 */
function generateWorkerPrompt(pane, worker, maxIterations) {
  const promptFile = path.join(PROMPTS_DIR, `${worker}.md`);
  
  let basePrompt = '';
  try {
    basePrompt = fs.readFileSync(promptFile, 'utf-8');
  } catch (error) {
    basePrompt = `You are a ${worker} worker. Research and develop trading strategies.`;
  }

  // Build the task execution prompt
  const taskPrompt = `
# Quant Research Team - Pane ${pane}

**Worker Type**: ${worker}
**Max Iterations**: ${maxIterations}
**Project Root**: ${PROJECT_ROOT}
**Backlog File**: ${path.join(STREAM_QUANT, 'backlogs', `pane-${pane}-${worker}.json`)}
**Output Directory**: ${path.join(STREAM_QUANT, 'output')}

---

${basePrompt}

---

## Your Autonomous Loop

Execute the following loop until all tasks are complete or max iterations reached:

1. **Read your backlog**: \`cat backlogs/pane-${pane}-${worker}.json\`
2. **Find next pending task**: Look for tasks with \`passes: false\`
3. **Execute the task** using your sub-agents and MCP tools
4. **Mark task complete** by updating the backlog file (set \`passes: true\`)
5. **Save checkpoint**: Write to \`checkpoints/pane-${pane}.checkpoint\`
6. **Repeat** until done

## Completion Markers

When you complete a task, output:
\`\`\`
QUANT_TASK_COMPLETE: [task-id]
OUTPUT: [path-to-output-file]
\`\`\`

## Start Now

Begin your first iteration. Read your backlog and execute the first pending task.
`;

  return taskPrompt;
}

/**
 * Generate AppleScript for iTerm2 automation
 * Runs quant-ralph.sh (proper Ralph Loop) in each pane
 */
function generateAppleScript(preset, maxIterations) {
  const workers = WORKER_ASSIGNMENTS[preset] || WORKER_ASSIGNMENTS.balanced;

  // Build command for each pane - runs the Ralph Loop script
  const paneCommands = workers.map(({ pane, worker }) => {
    const scriptPath = path.join(SCRIPTS_DIR, 'quant-ralph.sh');
    // Run Ralph Loop in the isolated quant worktree
    return `cd '${QUANT_WORKTREE}' && '${scriptPath}' ${pane} ${worker} ${maxIterations}`;
  });

  const script = `
tell application "iTerm"
  activate

  -- Create a new window
  create window with default profile

  tell current window
    tell current session of current tab
      -- Pane 1 (top-left) - Ralph Loop
      write text "${paneCommands[0]}"

      -- Split vertically to create Pane 2
      set pane2 to (split vertically with default profile)
      tell pane2
        write text "${paneCommands[1]}"

        -- Split vertically to create Pane 3
        set pane3 to (split vertically with default profile)
        tell pane3
          write text "${paneCommands[2]}"
        end tell
      end tell
    end tell

    -- Now split Pane 1 horizontally to create Pane 4
    tell session 1 of current tab
      set pane4 to (split horizontally with default profile)
      tell pane4
        write text "${paneCommands[3]}"
      end tell
    end tell

    -- Split Pane 2 horizontally to create Pane 5
    tell session 2 of current tab
      set pane5 to (split horizontally with default profile)
      tell pane5
        write text "${paneCommands[4]}"
      end tell
    end tell

    -- Split Pane 3 horizontally to create Pane 6
    tell session 3 of current tab
      set pane6 to (split horizontally with default profile)
      tell pane6
        write text "${paneCommands[5]}"
      end tell
    end tell

  end tell
end tell
`;

  return script;
}

/**
 * Send worker prompts to all panes
 * Called after Claude Code has initialized in each pane
 */
async function sendPromptsToAllPanes(preset, maxIterations) {
  const workers = WORKER_ASSIGNMENTS[preset] || WORKER_ASSIGNMENTS.balanced;

  console.log('\n📤 Sending prompts to all panes...');

  for (const { pane, worker } of workers) {
    const prompt = generateWorkerPrompt(pane, worker, maxIterations);
    
    // Session indices in iTerm after splits are: 1, 2, 3, 4, 5, 6
    // They correspond to panes 1-6 in order
    const success = sendToSession(pane, prompt);
    
    if (success) {
      console.log(`   ✅ Pane ${pane} (${worker}): prompt sent`);
    } else {
      console.log(`   ❌ Pane ${pane} (${worker}): failed to send prompt`);
    }

    // Small delay between panes to avoid overwhelming iTerm
    await sleep(500);
  }

  console.log('\n✅ All prompts sent!');
}

/**
 * Generate backlogs for all panes before launching
 */
function generateBacklogs(preset) {
  console.log('📋 Generating backlogs for all panes...');

  const generateScript = path.join(SCRIPTS_DIR, 'generate-backlog.py');

  try {
    const result = spawnSync('python3', [
      generateScript,
      '--preset', preset,
      '--regenerate'
    ], { stdio: 'inherit' });

    if (result.error) {
      throw new Error(`Failed to spawn python3: ${result.error.message}`);
    }
    if (result.status !== 0) {
      throw new Error(`Backlog generation failed with exit code ${result.status}`);
    }
    console.log('✅ Backlogs generated successfully');
  } catch (error) {
    console.error('❌ Failed to generate backlogs:', error.message);
    process.exit(1);
  }
}

/**
 * Initialize progress tracking
 */
function initializeProgress() {
  const progressFile = path.join(STREAM_QUANT, 'progress.json');
  const progress = {
    status: 'running',
    started_at: new Date().toISOString(),
    last_updated: new Date().toISOString(),
    panes: {},
  };

  fs.writeFileSync(progressFile, JSON.stringify(progress, null, 2));
  console.log('✅ Progress tracking initialized');
}

/**
 * Reset cost tracker for new session
 */
function resetCostTracker() {
  console.log('💰 Resetting cost tracker...');

  const costTrackerScript = path.join(SCRIPTS_DIR, 'cost-tracker.py');

  try {
    const result = spawnSync('python3', [costTrackerScript, 'status'], { stdio: 'pipe' });
    if (result.error) {
      throw new Error(`Failed to spawn python3: ${result.error.message}`);
    }
    if (result.status !== 0) {
      throw new Error(`Cost tracker status check failed with exit code ${result.status}`);
    }
    console.log('✅ Cost tracker ready');
  } catch (error) {
    console.warn('⚠️  Cost tracker not fully initialized, will initialize on first use');
  }
}

/**
 * Launch the iTerm2 window with Ralph Loop in each pane
 * Each pane runs quant-ralph.sh which handles the full loop
 */
function launchITerm(preset, maxIterations) {
  console.log(`\n🚀 Launching iTerm2 with Ralph Loop...`);
  console.log(`   Preset: ${preset}`);
  console.log(`   Max Iterations: ${maxIterations}`);
  console.log(`   Worktree: ${QUANT_WORKTREE}`);
  console.log(`   Panes: 6`);
  console.log('');

  const script = generateAppleScript(preset, maxIterations);

  try {
    // Write script to temp file
    const tempScript = '/tmp/quant-team-launcher.scpt';
    fs.writeFileSync(tempScript, script);

    // Execute AppleScript using execFileSync (no shell injection risk)
    execFileSync('osascript', [tempScript], { stdio: 'inherit' });

    console.log('✅ iTerm2 panes created with Ralph Loop running');

    // Clean up temp script
    fs.unlinkSync(tempScript);
    return true;
  } catch (error) {
    console.error('❌ Failed to launch iTerm:', error.message);
    return false;
  }
}

/**
 * Send startup notification
 */
function sendNotification() {
  const notifyScript = path.join(SCRIPTS_DIR, 'notify.py');

  try {
    spawnSync('python3', [
      notifyScript,
      'team_started',
      'Quant Research Team has started with 6 panes'
    ], { stdio: 'pipe' });
  } catch (error) {
    // Notification is optional, don't fail
  }
}

/**
 * Main entry point
 */
function main() {
  const args = process.argv.slice(2);
  const preset = args[0] || 'balanced';
  const maxIterations = parseInt(args[1], 10) || 50;

  // Validate preset
  if (!WORKER_ASSIGNMENTS[preset]) {
    console.error(`❌ Invalid preset: ${preset}`);
    console.error(`   Valid presets: ${Object.keys(WORKER_ASSIGNMENTS).join(', ')}`);
    process.exit(1);
  }

  console.log('╔════════════════════════════════════════════════════════════════╗');
  console.log('║           🧪 QUANT RESEARCH TEAM LAUNCHER (Ralph Loop)         ║');
  console.log('╚════════════════════════════════════════════════════════════════╝');

  // Pre-launch setup
  generateBacklogs(preset);
  initializeProgress();
  resetCostTracker();

  // Launch iTerm with Ralph Loop in each pane
  // Each pane runs quant-ralph.sh which handles:
  // - Claude Code spawning for each task
  // - Checkpointing between iterations
  // - Budget checks
  // - Completion notifications
  const launched = launchITerm(preset, maxIterations);
  if (!launched) {
    console.error('❌ Failed to launch. Exiting.');
    process.exit(1);
  }

  // Final output
  console.log('\n✅ Quant Research Team launched with Ralph Loop!');
  console.log(`\n📁 Worktree: ${QUANT_WORKTREE}`);
  console.log('\n📊 Monitor with: ./scripts/quant-team/quant-control.sh status');
  console.log('⏸️  Pause with:   ./scripts/quant-team/quant-control.sh pause');
  console.log('🛑 Stop with:    ./scripts/quant-team/quant-control.sh stop');

  // Send notification
  sendNotification();
}

// Run
main();
