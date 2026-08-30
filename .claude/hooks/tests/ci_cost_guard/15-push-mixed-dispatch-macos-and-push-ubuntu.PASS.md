# road-trip's actual shape: a dispatch-only macOS workflow beside a
# push-triggered ubuntu one -> PASS.
#
# The ubuntu run is a real cost and Patrick has said that cost is fine. Blocking
# it on macOS grounds refuses a justified push to prevent a spend that cannot
# occur. This is the fixture that represents the repo the ticket came from.
setup() {
  mkdir -p .github/workflows
  printf 'on:\n  workflow_dispatch:\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  printf 'on:\n  push:\n    branches: [develop]\njobs:\n  test:\n    runs-on: ubuntu-latest\n' > .github/workflows/ci.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin develop"
