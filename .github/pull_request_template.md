## What changed

<!-- The reasoning, not just the diff. -->

## Why

## Checks

- [ ] `python3 -m unittest discover -s tests -v`
- [ ] `python3 -m compileall -q plugins/talk-to-my-x tests`
- [ ] `npm run proofpress:verify`

## Constraints

- [ ] Every X read and write still goes through the official X Skill, `xurl`, or the official X MCP
- [ ] No new runtime, model call, web service, or third-party dependency in the state MCP
- [ ] All state stays local to the user's machine
- [ ] The two-stage confirmation before any X write is unchanged
- [ ] Setup-affecting changes update the README's install, verify, or troubleshooting sections
