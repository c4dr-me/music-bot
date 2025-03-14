
{pkgs}: {
  deps = [
    pkgs.openssh
    pkgs.imagemagick_light
    pkgs.lsof
    pkgs.pkg-config
    pkgs.libffi
    pkgs.libsodium
    pkgs.ffmpeg-full
    pkgs.libopus
  ];
}
