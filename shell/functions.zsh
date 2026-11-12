# Targets are always explicit; these helpers never install their own tools.
# Delete named local branches with Git's merge checks, then refresh remote branch listings.
# Usage: gclean BRANCH [BRANCH...]. Never uses force-delete.
gclean() {
  (( $# > 0 )) || { print -u2 'Usage: gclean BRANCH [BRANCH...] (merged branches only)'; return 2; }
  command git branch -d -- "$@" && command git fetch --prune
}

# Show the current time and connection delays to a host; requires prettyping.
# Usage: latency HOST [OPTIONS...]. Ctrl+C stops the check.
latency() {
  (( $# > 0 )) || { print -u2 'Usage: latency HOST [OPTIONS...]'; return 2; }
  command date && command prettyping "$@"
}

# Show weather from wttr.in; the supplied location is sent to that service.
# Usage: weather LOCATION (quote locations containing spaces). Requires curl and Python 3.
weather() {
  (( $# == 1 )) || { print -u2 'Usage: weather LOCATION'; return 2; }
  local location
  location="$(command python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1")" || return
  command curl -q --fail --silent --show-error "https://wttr.in/$location"
}

# Sign in to AWS through your browser using an existing named profile.
# Usage: laws PROFILE. Requires the AWS CLI with single sign-on configured.
laws() {
  (( $# == 1 )) || { print -u2 'Usage: laws PROFILE'; return 2; }
  command aws sso login --profile "$1"
}

# Sign in to Databricks profiles in order, stopping if any login fails.
# Usage: dlogin PROFILE [PROFILE...]. Requires the Databricks CLI.
dlogin() {
  (( $# > 0 )) || { print -u2 'Usage: dlogin PROFILE [PROFILE...]'; return 2; }
  local profile
  for profile in "$@"; do
    command databricks auth login --profile "$profile" || return
  done
}

# Unlock Bitwarden and keep BW_SESSION in this shell without printing it.
# Usage: bwu. Requires the bw CLI to be signed in already.
bwu() {
  emulate -L zsh
  setopt pipefail noxtrace
  local session
  session="$(command bw unlock --raw)" || return
  [[ -n "$session" ]] || { print -u2 'Vault unlock returned no session.'; return 1; }
  export BW_SESSION="$session"
}

# Load AWS credentials from Bitwarden into this shell; run bwu first.
# Usage: awslogin VAULT_ITEM AWS_PROFILE. Requires bw and jq.
# Item fields: aws_access_key_id, aws_secret_access_key, and optional aws_session_token.
# Failed reads keep existing credentials; a missing session token clears the old one.
awslogin() {
  emulate -L zsh
  setopt pipefail noxtrace
  (( $# == 2 )) || { print -u2 'Usage: awslogin VAULT_ITEM AWS_PROFILE'; return 2; }
  local item access secret token
  item="$(command bw get item "$1")" || return
  access="$(print -rn -- "$item" | command jq -er '.fields[]? | select(.name=="aws_access_key_id") | .value | select(type=="string" and length>0)' 2>/dev/null)" || { print -u2 'Vault item needs an access key.'; return 1; }
  secret="$(print -rn -- "$item" | command jq -er '.fields[]? | select(.name=="aws_secret_access_key") | .value | select(type=="string" and length>0)' 2>/dev/null)" || { print -u2 'Vault item needs a secret key.'; return 1; }
  token="$(print -rn -- "$item" | command jq -er '[.fields[]? | select(.name=="aws_session_token") | .value] | if length==0 then "" elif length==1 then .[0] | select(type=="string") else empty end' 2>/dev/null)" || return
  if [[ "$access$secret$token" == *$'\n'* || "$access$secret$token" == *$'\r'* ]]; then
    print -u2 'Vault credential fields must be single values.'
    return 1
  fi
  # Validate everything before replacing the current shell's credentials.
  export AWS_ACCESS_KEY_ID="$access" AWS_SECRET_ACCESS_KEY="$secret" AWS_PROFILE="$2"
  if [[ -n "$token" ]]; then
    export AWS_SESSION_TOKEN="$token"
  else
    unset AWS_SESSION_TOKEN
  fi
}

# Copy a Databricks secret's decoded value to the Mac clipboard, not the terminal.
# Usage: get-secret SECRET_NAME PROFILE SCOPE. Requires an authenticated Databricks CLI, jq, and Python 3.
# Failed lookups/decodes leave the clipboard alone. Clipboard managers may retain copied secrets.
get-secret() {
  emulate -L zsh
  setopt pipefail noxtrace
  (( $# == 3 )) || { print -u2 'Usage: get-secret SECRET_NAME PROFILE SCOPE'; return 2; }
  local encoded decoded
  encoded="$(command databricks secrets get-secret "$3" "$1" --profile "$2" | command jq -er '.value | select(type=="string" and length>0)' 2>/dev/null)" || return
  # Decode strictly before touching the clipboard; the final dot preserves trailing newlines.
  decoded="$(print -rn -- "$encoded" | command python3 -c 'import base64, sys; sys.stdout.buffer.write(base64.b64decode(sys.stdin.buffer.read(), validate=True) + b".")' 2>/dev/null)" || { print -u2 'Secret decoding failed; clipboard unchanged.'; return 1; }
  print -rn -- "${decoded%.}" | command pbcopy || return
  print 'Secret copied to clipboard.'
}
