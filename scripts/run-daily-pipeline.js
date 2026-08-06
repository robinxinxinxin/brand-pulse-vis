const fs = require("fs");
const path = require("path");
const childProcess = require("child_process");
const {
  DATA_DIR,
  ROOT,
  parseArgs,
  toDateKey
} = require("./lib/brandpulse-core");

function run(script, args) {
  const scriptPath = path.join(__dirname, script);
  const result = childProcess.spawnSync(process.execPath, [scriptPath, ...args], {
    cwd: ROOT,
    encoding: "utf8"
  });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.status !== 0) {
    throw new Error(`${script} failed with exit code ${result.status}`);
  }
}

function runPowerShell(script, args) {
  const scriptPath = path.join(__dirname, script);
  const result = childProcess.spawnSync("powershell.exe", [
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    scriptPath,
    ...args
  ], {
    cwd: ROOT,
    encoding: "utf8"
  });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.status !== 0) {
    throw new Error(`${script} failed with exit code ${result.status}`);
  }
}

function openDashboard() {
  const dashboardPath = path.join(ROOT, "index.html");
  const result = childProcess.spawnSync("cmd.exe", ["/c", "start", "", dashboardPath], {
    cwd: ROOT,
    encoding: "utf8",
    shell: false
  });
  if (result.status !== 0) {
    throw new Error(`open dashboard failed with exit code ${result.status}`);
  }
}

function main() {
  const args = parseArgs(process.argv);
  const dateKey = args.date || toDateKey();
  const dryRun = Boolean(args["dry-run"]);
  const shouldOpenDashboard = !dryRun && !args["no-open"];
  const rawCandidates = args.candidates || path.join(DATA_DIR, "candidates.raw.json");

  run("generate-search-keywords.js", ["--date", dateKey]);

  if (fs.existsSync(rawCandidates)) {
    run("score-candidates.js", ["--date", dateKey, "--input", rawCandidates]);
    run("dedupe-candidates.js", []);
  } else {
    console.log(`No raw candidates found at ${rawCandidates}; keyword plan only.`);
  }

  run("archive-products.js", ["--date", dateKey, ...(dryRun ? ["--dry-run"] : [])]);
  run("sync-last-updated.js", ["--date", dateKey, ...(dryRun ? ["--dry-run"] : [])]);
  if (!dryRun) {
    runPowerShell("validate-brandpulse.ps1", []);
  }
  if (shouldOpenDashboard) {
    openDashboard();
  }

  console.log(`Daily scripted pipeline complete for ${dateKey}${dryRun ? " (dry run)" : ""}${shouldOpenDashboard ? "; dashboard opened" : ""}.`);
}

main();
