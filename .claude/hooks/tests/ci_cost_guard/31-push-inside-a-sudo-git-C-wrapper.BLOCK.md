# A push behind `sudo` and aimed with `git -C` -> BLOCK.
#
# CH-237.10, defect 2, third shape, named in the finding as
# `sudo git -C <ios> push`. argv0 was sudo so _kind saw nothing, and the
# wrapper hid the push from the guard entirely.
setup() {
  mkdir -p ios && ( cd ios && git init -q \
    && git config user.email t@example.com && git config user.name t )
  mkdir -p ios/.github/workflows
  printf 'on:\n  push:\njobs:\n  build:\n    runs-on: macos-15\n' \
    > ios/.github/workflows/ios.yml
}
COMMAND="sudo git -C ios push origin main"
