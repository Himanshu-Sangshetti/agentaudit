Output video/public/walkthrough.mp4

Set Shell zsh
Set FontFamily "JetBrains Mono"
Set FontSize 40
Set Width 3280
Set Height 4300
Set Padding 72
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Set WindowBar Colorful
Set BorderRadius 24
Set Margin 0

Hide
Type "cd ~/huggingface-challenge && source video/tapes/setup.sh"
Enter
Sleep 2s
Show

Type "# Payroll Helper: an HR agent, before it goes live"
Sleep 600ms
Enter
Type "agentaudit scan examples/payroll-helper.yaml --registry examples/demo_registry"
Sleep 600ms
Enter
Wait+Screen@120s /credits spent/
Sleep 1.5s
Type "echo exit=$?"
Enter
Sleep 4s
