
{pkgs}: {
  deps = [
    pkgs.pkg-config
    pkgs.libffi
    pkgs.libsodium
    pkgs.ffmpeg-full
    pkgs.libopus
  ];
}
