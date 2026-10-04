# ==============================================================================
# Qtile Settings & Command Center - Nix Flake Specification
# Provides packages, apps (default, quick), devShells, NixOS & Home Manager modules
# ==============================================================================
{
  description = "Qtile Settings & Command Center - Modern PySide6 settings center for Qtile on X11";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      # Supported architecture architectures on Linux
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "i686-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems (system: f {
        pkgs = import nixpkgs { inherit system; };
        inherit system;
      });
    in {
      # 1. Package Derivations
      packages = forAllSystems ({ pkgs, ... }: rec {
        default = qtile-settings;
        qtile-settings = pkgs.python3Packages.buildPythonApplication {
          pname = "qtile-settings";
          version = "0.1.0";
          pyproject = true;

          src = ./.;

          # Build tool dependencies
          build-system = with pkgs.python3Packages; [
            setuptools
            wheel
          ];

          # Python runtime library dependencies
          dependencies = with pkgs.python3Packages; [
            pyside6
            psutil
          ];

          # Hook to wrap Qt binaries with appropriate platform plugins
          nativeBuildInputs = [
            pkgs.qt6.wrapQtAppsHook
          ];

          # Prefix PATH with necessary external CLI tools
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
        };
      });

      # 2. Executable Apps ('nix run .' and 'nix run .#quick')
      apps = forAllSystems ({ pkgs, system }: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/qtile-settings";
        };
        quick = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/qtile-settings";
        };
      });

      # 3. Interactive Development Shell ('nix develop')
      devShells = forAllSystems ({ pkgs, ... }: {
        default = pkgs.mkShell {
          packages = [
            pkgs.python3
            pkgs.python3Packages.pyside6
            pkgs.python3Packages.psutil
            pkgs.python3Packages.pytest
            pkgs.python3Packages.ruff
            pkgs.qt6.wrapQtAppsHook
            pkgs.brightnessctl
            pkgs.networkmanager
            pkgs.wireplumber
          ];
          shellHook = ''
            export QT_QPA_PLATFORM="xcb;offscreen"
            echo "Qtile Settings development environment ready."
          '';
        };
      });

      # 4. NixOS System Configuration Module
      nixosModules.default = { config, lib, pkgs, ... }:
        let
          cfg = config.programs.qtile-settings;
        in {
          options.programs.qtile-settings = {
            enable = lib.mkEnableOption "Qtile Settings & Command Center";
          };

          config = lib.mkIf cfg.enable {
            environment.systemPackages = [
              self.packages.${pkgs.system}.default
            ];
          };
        };

      # 5. Home Manager User Configuration Module
      homeManagerModules.default = { config, lib, pkgs, ... }:
        let
          cfg = config.programs.qtile-settings;
        in {
          options.programs.qtile-settings = {
            enable = lib.mkEnableOption "Qtile Settings & Command Center";
          };

          config = lib.mkIf cfg.enable {
            home.packages = [
              self.packages.${pkgs.system}.default
            ];
          };
        };
    };
}
