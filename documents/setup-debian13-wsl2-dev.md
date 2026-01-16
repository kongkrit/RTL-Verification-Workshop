## Debian 13 WSL2 Setup for BareMetal-C-Dev
Click start and type:
```
turn windows features on or off
```
scroll down and check `Windows Subsystem for Linux`.

Reboot if necessary.
### Check your current WSL version:
Type `Win+R` and run `cmd` or `powershell`:
```
wsl --version
```
If it says `WSL version: 2.x`, you're ok,
> but if it is `1.x`, you must update `WSL` to `WSL2` by:
> ```
> wsl --update
> ```
> Reboot if necessary.

Now do the safety check.
```
wsl --list
```
If it contains `Debian`, proceed at your own risk!
### Install Debian
```
wsl --install Debian
```
This will take a while. You'll be asked for a new username. Use
```
baremetal-dev
```
and just add a simple password (type it twice). We won't be doing anything unsecure on this machine.
### update `sudo` so we can do it without password
Your prompt should now read: `dev@something:/mnt/c/Users/name$`, type:
```bash
sudo visudo
```
give the password. scroll down this file until you see: `%sudo   ALL=(ALL:ALL) ALL`. Add a new line below it and type:
```
baremetal-dev ALL=(ALL) NOPASSWD: ALL
```
so now that part reads:
> ```
> # Allow...
> %sudo   ALL=(ALL:ALL) ALL
> baremetal-dev ALL=(ALL) NOPASSWD: ALL
> 
> # See...
> ```
Type: `ctrl-o`, type `enter`, then `ctrl-x`, you will be back at `dev@something:/mnt/c/Users/name$`
### Prettify:
- Print out distro name and alias `l` `ll` `la`
- Change `ls` colors
- Change prompt
```bash
cat <<'EOF' >> ~/.bashrc

alias ls='ls --color=auto'
alias l='ls -CF --color=auto'
alias la='ls -A --color=auto'
alias ll='ls -l --color=auto'
alias vim='vi'

export LS_COLORS='di=00;36:ow=01;36:st=01;36:ex=01;32:ln=01;36'

export PS1='\[\033[01;33m\][\u]\[\033[00m\]:\[\033[01;36m\]\w\[\033[00m\] \$ '
# --- Distro display ---
if [ -f /etc/os-release ]; then
    . /etc/os-release
    PS1="(${ID^})$PS1"
fi

# --- Guard to prevent double welcome message ---
if [ -z "$BAREMETAL_WELCOME_SHOWN" ]; then
    echo -e "\033[1;32mWelcome to WSL BareMetal-C-Dev Environment\033[0m"
    ver | xargs
    export BAREMETAL_WELCOME_SHOWN=true
fi
EOF
```
> ### Optional but very nice `gocode` alias
> You need to modify `YOURNAME` and `YOURPATH` to match your environment. Then,
> ```bash
> cat << 'EOF' >> ~/.bashrc
> 
> alias gocode='cd /mnt/c/Users/YOURNAME/YOURPATH/BareMetal-C-Labs/code/'
> EOF
> ```
and run it
```bash
source ~/.bashrc
```
Now your prompt will be: `(Debian)[baremetal-dev]:/mnt/c/Users/name $`
### Update system
```bash
sudo apt update && sudo apt upgrade -y
```
### Install `git` and `gh`
```bash
sudo apt install -y git gh
```

---

### Log out and set WSL networking to `Mirrored`
At the prompt, type:
```
exit
```
You will be returned to Windows, with something similar to `C:\Users\username> `

click windows start menu, type in `wsl settings` and run it (the blue-head penguin).

Click `Networking` tab on the left. On the right, select `Networking Mode` to be `Mirrored`.
#### Double check that your networking is now `mirrored`:
Check for the content of file: `C:\Users\NAME\.wslconfig` and it should have this section:
```
[wsl2]
networkingMode=Mirrored
```

---
## Further info:

**Make Debian the default distro when running `wsl`:**
```
wsl --set-default Debian
```
Check that it is truly the default ( `*` in front of the name):
```
wsl -l -v
```
How to launch a specific distro:
```
wsl -d <DistributionName>
```

### Restart WSL
Either:
- Open start menu and look for `Debian` and run it
- Start `cmd` and run:
  ```
  wsl -d Debian
  ```
You will be back at `(Debian)[baremetal-dev]:/mnt/c/Users/name $` prompt.
