#!/usr/bin/env bash

# Read-only development environment verification for this repository.
# The script reports all failures before exiting and never installs or changes tools.

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
failures=0

pass() {
  printf 'PASS: %s\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1"
  failures=$((failures + 1))
}

info() {
  printf 'INFO: %s\n' "$1"
}

first_line() {
  printf '%s\n' "$1" | sed -n '1p'
}

check_version_command() {
  label="$1"
  command_name="$2"
  shift 2

  if ! command -v "${command_name}" >/dev/null 2>&1; then
    fail "${label} command is unavailable (${command_name})"
    return
  fi

  output="$("${command_name}" "$@" 2>&1)"
  status=$?
  if [ "${status}" -ne 0 ]; then
    fail "${label} command failed with exit ${status}"
    return
  fi

  pass "${label}: $(first_line "${output}")"
}

resolve_android_tool() {
  tool_name="$1"
  relative_path="$2"

  if command -v "${tool_name}" >/dev/null 2>&1; then
    command -v "${tool_name}"
    return 0
  fi

  if [ -n "${android_sdk_root}" ] && [ -x "${android_sdk_root}/${relative_path}" ]; then
    printf '%s\n' "${android_sdk_root}/${relative_path}"
    return 0
  fi

  return 1
}

os_name="$(uname -s)"
architecture="$(uname -m)"
pass "Host: ${os_name} ${architecture}"

if [ "${os_name}" = "Darwin" ]; then
  if command -v sw_vers >/dev/null 2>&1; then
    macos_version="$(sw_vers -productVersion)"
    pass "macOS: ${macos_version}"
  else
    fail "sw_vers is unavailable"
  fi

  if xcode_path="$(xcode-select -p 2>/dev/null)"; then
    pass "Xcode Command Line Tools are selected"
  else
    fail "Xcode Command Line Tools are unavailable; run: xcode-select --install"
  fi

  check_version_command "Homebrew" "brew" "--version"
fi

check_version_command "Git" "git" "--version"

if command -v java >/dev/null 2>&1; then
  java_version="$(java -version 2>&1)"
  java_summary="$(first_line "${java_version}")"
  if printf '%s\n' "${java_summary}" | grep -Eq 'version "21(\.|")'; then
    pass "Java: ${java_summary}"
  else
    fail "Java must report JDK 21; detected ${java_summary}"
  fi
else
  fail "Java command is unavailable (java)"
fi

if command -v node >/dev/null 2>&1; then
  node_version="$(node --version 2>&1)"
  node_lts="$(node -p 'process.release.lts || ""' 2>/dev/null)"
  if [ -n "${node_lts}" ]; then
    pass "Node.js: ${node_version} LTS (${node_lts})"
  else
    fail "Node.js ${node_version} is not an LTS release"
  fi
else
  fail "Node.js command is unavailable (node)"
fi

check_version_command "npm" "npm" "--version"
check_version_command "Codex CLI" "codex" "--version"

python_version=""
if command -v python >/dev/null 2>&1; then
  python_version="$(python --version 2>&1)"
  if printf '%s\n' "${python_version}" | grep -Eq '^Python 3\.12(\.|$)'; then
    pass "Python: ${python_version}"
  else
    fail "python must report Python 3.12.x; detected ${python_version}"
  fi
else
  fail "python command is unavailable; it must resolve to Python 3.12.x"
fi

if command -v python3 >/dev/null 2>&1; then
  info "python3: $(python3 --version 2>&1)"
else
  info "python3: unavailable"
fi

if command -v python3.12 >/dev/null 2>&1; then
  info "python3.12: $(python3.12 --version 2>&1)"
else
  info "python3.12: unavailable"
fi

if [ "${os_name}" = "Darwin" ]; then
  if [ -d "/Applications/Android Studio.app" ]; then
    android_studio_version="$(
      defaults read "/Applications/Android Studio.app/Contents/Info.plist" \
        CFBundleShortVersionString 2>/dev/null
    )"
    if [ -n "${android_studio_version}" ]; then
      pass "Android Studio: ${android_studio_version}"
    else
      pass "Android Studio application is installed"
    fi
  else
    fail "Android Studio is not installed in /Applications"
  fi
else
  info "Verify Android Studio installation manually on this operating system"
fi

android_sdk_root="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [ -z "${android_sdk_root}" ] && [ -f "${REPO_ROOT}/android/local.properties" ]; then
  android_sdk_root="$(
    sed -n 's/^sdk\.dir=//p' "${REPO_ROOT}/android/local.properties" | sed -n '1p'
  )"
fi

if [ -n "${android_sdk_root}" ] && [ -d "${android_sdk_root}" ]; then
  pass "Android SDK root is configured"
else
  fail "Android SDK root is unavailable; set ANDROID_HOME or android/local.properties"
  android_sdk_root=""
fi

if adb_path="$(resolve_android_tool "adb" "platform-tools/adb")"; then
  adb_output="$("${adb_path}" version 2>&1)"
  adb_status=$?
  if [ "${adb_status}" -eq 0 ]; then
    adb_summary="$(printf '%s\n' "${adb_output}" | sed -n '1,2p' | tr '\n' ' ')"
    pass "adb: ${adb_summary% }"
  else
    fail "adb failed with exit ${adb_status}"
  fi
else
  fail "adb is unavailable; install Android SDK Platform-Tools"
fi

if emulator_path="$(resolve_android_tool "emulator" "emulator/emulator")"; then
  emulator_output="$("${emulator_path}" -version 2>&1)"
  emulator_status=$?
  if [ "${emulator_status}" -eq 0 ]; then
    pass "Android Emulator: $(first_line "${emulator_output}")"
  else
    fail "Android Emulator version check failed with exit ${emulator_status}"
  fi

  if [ "${os_name}" = "Darwin" ]; then
    accel_output="$("${emulator_path}" -accel-check 2>&1)"
    accel_status=$?
    if [ "${accel_status}" -eq 0 ]; then
      pass "Android Emulator acceleration is available"
    else
      fail "Android Emulator acceleration check failed with exit ${accel_status}"
    fi
  fi

  avd_output="$("${emulator_path}" -list-avds 2>&1)"
  avd_status=$?
  if [ "${avd_status}" -ne 0 ]; then
    fail "Android Virtual Device listing failed with exit ${avd_status}"
  elif [ -z "${avd_output}" ]; then
    fail "No Android Virtual Device is configured"
  else
    avd_count="$(printf '%s\n' "${avd_output}" | sed '/^[[:space:]]*$/d' | wc -l | tr -d ' ')"
    pass "Android Virtual Devices configured: ${avd_count}"
  fi
else
  fail "Android Emulator is unavailable"
fi

if sdkmanager_path="$(resolve_android_tool "sdkmanager" "cmdline-tools/latest/bin/sdkmanager")"; then
  sdkmanager_output="$("${sdkmanager_path}" --version 2>&1)"
  sdkmanager_status=$?
  if [ "${sdkmanager_status}" -eq 0 ]; then
    pass "sdkmanager: $(first_line "${sdkmanager_output}")"
  else
    fail "sdkmanager failed with exit ${sdkmanager_status}"
  fi
else
  fail "sdkmanager is unavailable; install Android SDK Command-line Tools (latest)"
fi

if [ -n "${android_sdk_root}" ] && [ -d "${android_sdk_root}/platforms/android-36.1" ]; then
  pass "Android SDK Platform android-36.1 is installed"
else
  fail "Android SDK Platform android-36.1 is unavailable"
fi

if [ -n "${android_sdk_root}" ] && [ -d "${android_sdk_root}/build-tools/36.0.0" ]; then
  pass "Android SDK Build-Tools 36.0.0 are installed"
else
  fail "Android SDK Build-Tools 36.0.0 are unavailable"
fi

gradle_output="$(cd "${REPO_ROOT}" && ./android/gradlew --version 2>&1)"
gradle_status=$?
if [ "${gradle_status}" -eq 0 ]; then
  gradle_version="$(printf '%s\n' "${gradle_output}" | sed -n 's/^Gradle /Gradle /p' | sed -n '1p')"
  pass "Android Gradle wrapper: ${gradle_version:-version command succeeded}"
else
  fail "Android Gradle wrapper failed with exit ${gradle_status}"
fi

if command -v docker >/dev/null 2>&1; then
  docker_version="$(docker --version 2>&1)"
  docker_cli_status=$?
  if [ "${docker_cli_status}" -eq 0 ]; then
    pass "Docker CLI: ${docker_version}"
  else
    fail "Docker CLI version check failed with exit ${docker_cli_status}"
  fi

  docker_server_version="$(docker info --format '{{.ServerVersion}}' 2>/dev/null)"
  docker_daemon_status=$?
  if [ "${docker_daemon_status}" -eq 0 ] && [ -n "${docker_server_version}" ]; then
    pass "Docker daemon: server ${docker_server_version}"
  else
    fail "Docker daemon is unavailable; start Docker Desktop and rerun docker info"
  fi
else
  fail "Docker CLI is unavailable"
  fail "Docker daemon cannot be checked without the Docker CLI"
fi

if [ "${failures}" -eq 0 ]; then
  printf '\nEnvironment verification passed.\n'
  exit 0
fi

printf '\nEnvironment verification failed with %s issue(s).\n' "${failures}"
exit 1
