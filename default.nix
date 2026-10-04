# ==============================================================================
# Qtile Settings & Command Center - Classic Nix Derivation
# Supports classic nix-shell and Nix environments on Linux
# ==============================================================================
{ pkgs ? import <nixpkgs> {} }:

pkgs.python3Packages.buildPythonApplication {
  pname = "qtile-settings";
  version = "0.1.0";
  pyproject = true;

  src = ./.;

  # Python packaging build dependencies
  build-system = with pkgs.python3Packages; [
    setuptools
    wheel
  ];

  # Runtime Python library dependencies
  dependencies = with pkgs.python3Packages; [
    pyside6
    psutil
  ];

  # Qt hook to wrap binaries with appropriate QT_PLUGIN_PATH and display plugins
  nativeBuildInputs = [
    pkgs.qt6.wrapQtAppsHook
  ];

  # Ensure essential external system tools are prefixed into runtime PATH
  makeWrapperArgs = [
    "--prefix" "PATH" ":" "${pkgs.lib.makeBinPath (with pkgs; [
      brightnessctl
      networkmanager
      wireplumber
      pulseaudio
      xorg.xrandr
      xorg.xinput
      feh
      qtile
    ])}"
  ];

  meta = with pkgs.lib; {
    description = "Settings & Session Command Center for Qtile Window Manager";
    license = licenses.mit;
    mainProgram = "qtile-settings";
    platforms = platforms.linux;
  };
}
