Output video/public/walkthrough.mp4

Set Shell zsh
Set FontFamily "JetBrains Mono"
Set FontSize 20
Set Width 1640
Set Height 2400
Set Padding 36
Set Theme "Catppuccin Mocha"
Set TypingSpeed 38ms
Set WindowBar Colorful
Set BorderRadius 14
Set Margin 0

Hide
Type "cd ~/huggingface-challenge && source video/tapes/setup.sh"
Enter
Sleep 2s
Show

Type "# a skill downloaded from a marketplace"
Sleep 600ms
Enter
Type "agentaudit scan examples/pdf-tools-skill.yaml"
Sleep 500ms
Enter
Wait+Screen@120s /credits spent/
Sleep 6s

Type "clear"
Enter
Type "# an in-house payroll agent, checked against the approved registry"
Sleep 600ms
Enter
Type "agentaudit scan examples/payroll-helper.yaml --registry examples/demo_registry"
Sleep 500ms
Enter
Wait+Screen@120s /credits spent/
Sleep 7s

Type "echo exit=$?"
Enter
Sleep 2.5s
