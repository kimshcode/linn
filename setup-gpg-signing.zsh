#!/usr/bin/env zsh
set -euo pipefail

print_step() { print -P "%F{cyan}==> %f%B$1%b" }
print_ok()   { print -P "%F{green}✓%f $1" }
print_err()  { print -P "%F{red}✗%f $1" >&2 }

# Check dependencies
for cmd in gpg git; do
    if ! command -v $cmd &>/dev/null; then
        print_err "$cmd is not installed."
        if [[ $cmd == "gpg" ]]; then
            print "  Install with: brew install gnupg"
        fi
        exit 1
    fi
done

print_step "GPG Commit Signing Setup"
print ""

# List existing keys
existing_keys=$(gpg --list-secret-keys --keyid-format long 2>/dev/null || true)

if [[ -n "$existing_keys" ]]; then
    print_step "Existing GPG keys found:"
    print "$existing_keys"
    print ""
    vared -p "Use an existing key? [y/N] " -c use_existing
else
    use_existing="n"
fi

if [[ "${use_existing:l}" == "y" ]]; then
    vared -p "Enter the key ID (the hex string after sec rsa/ed25519): " -c key_id
else
    print_step "Generating a new GPG key"
    print ""

    vared -p "Full name (for key identity): " -c full_name
    vared -p "Email address (must match your Git commits): " -c email

    # Prefer ed25519 if supported, fall back to rsa4096
    gpg_version=$(gpg --version | head -1 | grep -oE '[0-9]+\.[0-9]+')
    if (( $(print "$gpg_version >= 2.1" | bc -l) )); then
        key_algo="ed25519"
        print_ok "Using Ed25519 (GPG $gpg_version supports it)"
    else
        key_algo="rsa4096"
        print_ok "Using RSA-4096 (GPG $gpg_version)"
    fi

    if [[ $key_algo == "ed25519" ]]; then
        gpg --batch --passphrase '' --quick-gen-key "$full_name <$email>" ed25519 sign 0
    else
        cat <<GPGEOF | gpg --batch --gen-key
Key-Type: RSA
Key-Length: 4096
Name-Real: $full_name
Name-Email: $email
Expire-Date: 0
%no-protection
%commit
GPGEOF
    fi

    key_id=$(gpg --list-secret-keys --keyid-format long "$email" 2>/dev/null \
        | grep -E "^\s*(sec|ssb)" | head -1 | grep -oE '[A-F0-9]{16}')

    if [[ -z "$key_id" ]]; then
        print_err "Failed to retrieve the generated key ID."
        exit 1
    fi

    print_ok "Key generated: $key_id"
fi

print ""
print_step "Configuring Git to use GPG key $key_id"

vared -p "Apply globally? [Y/n] " -c apply_global
scope=""
[[ "${apply_global:l}" != "n" ]] && scope="--global"

git config $scope user.signingkey "$key_id"
git config $scope commit.gpgsign true
git config $scope tag.gpgsign true
git config $scope gpg.program "$(command -v gpg)"

print_ok "Git config updated (commit.gpgsign=true, tag.gpgsign=true)"

# Configure gpg-agent for passphrase caching
gpg_agent_conf="${GNUPGHOME:-$HOME/.gnupg}/gpg-agent.conf"
mkdir -p "$(dirname "$gpg_agent_conf")"

if ! grep -q "pinentry-program" "$gpg_agent_conf" 2>/dev/null; then
    pinentry_mac=$(command -v pinentry-mac 2>/dev/null || true)
    if [[ -n "$pinentry_mac" ]]; then
        print "pinentry-program $pinentry_mac" >> "$gpg_agent_conf"
        print_ok "Configured pinentry-mac for passphrase prompts"
    else
        print "  Tip: brew install pinentry-mac for a native macOS passphrase dialog"
    fi
fi

if ! grep -q "default-cache-ttl" "$gpg_agent_conf" 2>/dev/null; then
    cat >> "$gpg_agent_conf" <<EOF
default-cache-ttl 3600
max-cache-ttl 86400
EOF
    print_ok "Set passphrase cache TTL (1h default, 24h max)"
fi

gpg-connect-agent reloadagent /bye &>/dev/null || true

# Export public key for adding to GitHub/GitLab
print ""
print_step "Your GPG public key (add this to GitHub/GitLab):"
print ""
gpg --armor --export "$key_id"
print ""

print_step "Setup complete!"
print ""
print "  Next steps:"
print "  1. Copy the public key above"
print "  2. Add it to your Git host:"
print "     - GitHub:  Settings → SSH and GPG keys → New GPG key"
print "     - GitLab:  Preferences → GPG Keys"
print "  3. Test with: git commit --allow-empty -m 'test gpg signing'"
print "  4. Verify with: git log --show-signature -1"
print ""

# Shell environment hint
if ! grep -q "GPG_TTY" ~/.zshrc 2>/dev/null; then
    print "  Add this to your ~/.zshrc for terminal passphrase prompts:"
    print '    export GPG_TTY=$(tty)'
    print ""
    vared -p "  Add it now? [Y/n] " -c add_tty
    if [[ "${add_tty:l}" != "n" ]]; then
        print '\nexport GPG_TTY=$(tty)' >> ~/.zshrc
        print_ok "Added GPG_TTY to ~/.zshrc"
    fi
fi
