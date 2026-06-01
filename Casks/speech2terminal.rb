cask "speech2terminal" do
  version "0.0.0"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"

  url "https://github.com/templegit9/speech2terminal/releases/download/v#{version}/speech2terminal-#{version}.zip"
  name "speech2terminal"
  desc "Voice-driven terminal dictation (local MLX Whisper)"
  homepage "https://github.com/templegit9/speech2terminal"

  depends_on macos: ">= :ventura"

  app "speech2terminal.app"

  zap trash: [
    "~/.config/speech2terminal",
    "~/Library/Caches/com.oluyinka.speech2terminal",
  ]
end
