# Reference copy of the Homebrew cask. The source of truth lives in the tap
# repo (templegit9/homebrew-speech2terminal, Casks/speech2terminal.rb) and is
# rewritten by packaging/release.sh on each release. This copy documents the
# shape and lets you eyeball it in the app repo.
cask "speech2terminal" do
  version "0.1.0"
  sha256 :no_check # release.sh fills the real digest in the tap

  url "https://github.com/templegit9/speech2terminal/releases/download/v#{version}/speech2terminal-#{version}.zip"
  name "speech2terminal"
  desc "Voice-driven terminal dictation (local MLX Whisper)"
  homepage "https://github.com/templegit9/speech2terminal"

  depends_on macos: ">= :ventura"

  app "speech2terminal.app"

  zap trash: [
    "~/.config/speech2terminal",
    "~/Library/Caches/com.oginni.speech2terminal",
  ]
end
