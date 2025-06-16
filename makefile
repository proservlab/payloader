# ──────────────────────────────────────────────
# Makefile – local lint helpers
#
# Targets
#   make deps      – interactively install required tools
#   make shellcheck
#   make pssa
#   make readme
#   make lint      – run everything (default)
# ──────────────────────────────────────────────

SHELL   := /usr/bin/env bash
.DEFAULT_GOAL := lint

SHELL_SCRIPTS   := $(shell find . -type f -name '*.sh')
POWERSHELL_SCRIPTS := $(shell find . -type f -name '*.ps1')
PYTHON_SCRIPTS := $(shell find . -type f -name '*.py' -not -path "*/venv/*")

# ────────────── dependency helpers ─────────────

define NEED_TOOL
  @$$(command -v $(1) >/dev/null 2>&1) || \
    { echo "❌  '$(1)' not found. Run 'make deps' to install." ; exit 1; }
endef

deps:
	@bash -c '\
	  set -e; \
	  echo "📦  Checking tools..."; \
	  pkg=""; OS=$$(uname -s); \
	  if command -v apt-get >/dev/null;  then pkg="sudo apt-get install -y"; \
	  elif command -v yum >/dev/null;     then pkg="sudo yum install -y"; \
	  elif command -v brew >/dev/null;    then pkg="brew install"; \
	  else echo "⚠️  No supported package manager detected (apt, yum, brew)"; exit 1; fi; \
	  echo "Detected package manager: $$pkg"; \
	  for t in shellcheck jq pwsh python3; do \
	    if ! command -v $$t >/dev/null 2>&1; then \
	      read -p \"Install $$t? [y/N] \" yn; \
	      case $$yn in [Yy]*) echo \"→ Installing $$t\"; $$pkg $$t ;; *) echo \"Skipping $$t\" ;; esac; \
	    fi; \
	  done; \
	  echo \"Installing PowerShell module PSScriptAnalyzer if missing...\"; \
	  if command -v pwsh >/dev/null 2>&1; then \
	    pwsh -NoLogo -Command '\
	      if (-not (Get-Module -ListAvailable -Name PSScriptAnalyzer)) { \
	        Install-Module PSScriptAnalyzer -Force -Scope CurrentUser; \
	      }'; \
	  fi'

# ────────────── ShellCheck ─────────────

.PHONY: shellcheck
shellcheck:
	$(call NEED_TOOL,shellcheck)
	$(call NEED_TOOL,jq)
	@echo "🔍  ShellCheck..."
	@set -e; \
	if [ -z "$(SHELL_SCRIPTS)" ]; then echo "No Linux scripts." ; exit 0; fi; \
	shellcheck -S error $(SHELL_SCRIPTS) --exclude=2148 -f json | \
	  tee shellcheck.json > /dev/null; \
	ERRORS=$$(jq '[.[] | select(.level=="error")] | length' shellcheck.json); \
	echo "ShellCheck errors: $$ERRORS"; \
	if [[ $$ERRORS -gt 0 ]]; then \
	  echo "❌  ShellCheck errors found"; \
	  cat shellcheck.json | jq; \
	  exit 1; \
	fi;
	@echo "✅  ShellCheck passed (no errors)."

# ────────────── PSScriptAnalyzer ─────────────

.PHONY: pssa
pssa:
	$(call NEED_TOOL,pwsh)
	@echo "🔍  PSScriptAnalyzer..."
	@pwsh -NoLogo -Command '\
	  $$ErrorActionPreference="Stop"; \
	  $$scripts = "$(POWERSHELL_SCRIPTS)".Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries); \
	  if (-not $$scripts) { Write-Host "No Windows scripts."; exit 0 }; \
	  $$results = Invoke-ScriptAnalyzer -Path ./client/*.ps1 -Severity Error -ExcludeRule "PSAvoidUsingConvertToSecureStringWithPlainText"; \
	  $$results | ConvertTo-Json -Depth 10 | Out-File scriptanalyzer.json -Encoding utf8; \
	  if ($$results.Count -ne 0) { Write-Output "ScriptAnalyzer errors found"; Get-Content scriptanalyzer.json | jq; exit 1 } \
	  else { Write-Host "✅  ScriptAnalyzer passed (no errors)." }'

# ────────────── pythoncheck coverage ─────────────

.PHONY: flake8
flake8:
	$(call NEED_TOOL,python3)
	@echo "🔍  Python coverage..."
	@bash -c '\
	  set -eo pipefail; missing=(); \
	  python3 -m venv venv > /dev/null 2>&1; \
	  source venv/bin/activate > /dev/null 2>&1; \
	  pip install flake8 black isort > /dev/null 2>&1; \
	  for script in $(PYTHON_SCRIPTS); do \
	  	if ! black $$script --line-length 120 --preview > /dev/null 2>&1; then \
	      echo "❌  Black errors found in $$script"; exit 1; \
	    fi; \
	    if ! isort $$script; then \
	      echo "❌  Isort errors found in $$script"; exit 1; \
	    fi; \
	    if ! flake8 --max-line-length=120 --ignore=E402,F841,F401,E302,E305,W503 $$script; then \
	      echo "❌  Flake8 errors found in $$script"; exit 1; \
	    fi; \
	  done; \
	  echo "✅  Flake8 passed.";'

# ────────────── aggregate target ─────────────

.PHONY: lint
lint: shellcheck pssa flake8
	@echo "🎉  All lint checks passed."