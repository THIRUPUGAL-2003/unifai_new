{
  description = "UnifAI's Nix Flake";

  # Flake inputs
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/staging-next";
  };

  # Flake outputs
  outputs =
    { self, ... }@inputs:
    let
      # The systems supported for this flake's outputs
      supportedSystems = [
        "x86_64-linux" # 64-bit Intel/AMD Linux
        "aarch64-linux" # 64-bit ARM Linux
        "aarch64-darwin" # 64-bit ARM macOS
      ];

      # Temporary workaround until nixpkgs includes Go 1.26.4.
      go_1_26_4_overlay = final: prev: {
        go_1_26 = prev.go_1_26.overrideAttrs (oldAttrs: rec {
          version = "1.26.4";
          src = final.fetchurl {
            url = "https://go.dev/dl/go${version}.src.tar.gz";
            sha256 = "0bb089d2bfszfc8r4cra94qsdb8x5y69dyw1m3k344gwzcr8lrjg";
          };
        });
        go = final.go_1_26;
      };

      # Helper for providing system-specific attributes
      forEachSupportedSystem =
        f:
        inputs.nixpkgs.lib.genAttrs supportedSystems (
          system:
          f {
            inherit system;
            # Provides a system-specific, configured Nixpkgs
            pkgs = import inputs.nixpkgs {
              inherit system;
              overlays = [ go_1_26_4_overlay ];
              # Enable using unfree packages
              config.allowUnfree = true;
            };
          }
        );
    in
    {
      nixosModules = {
        unifai =
          { pkgs, lib, ... }:
          {
            imports = [ ./nix/modules/unifai.nix ];
            services.unifai.package = lib.mkDefault self.packages.${pkgs.system}.unifai-http;
          };
      };

      packages = forEachSupportedSystem (
        {
          pkgs,
          system,
        }:
        let
          version = "1.4.9";

          unifai-ui = pkgs.callPackage ./nix/packages/unifai-ui.nix {
            src = self;
            inherit version;
          };
        in
        {
          unifai-ui = unifai-ui;

          unifai-http = pkgs.callPackage ./nix/packages/unifai-http.nix {
            inherit inputs;
            src = self;
            inherit version;
            inherit unifai-ui;
          };

          default = self.packages.${system}.unifai-http;
        }
      );

      apps = forEachSupportedSystem (
        { system, ... }:
        {
          unifai-http = {
            type = "app";
            program = "${self.packages.${system}.unifai-http}/bin/unifai-http";
          };

          default = self.apps.${system}.unifai-http;
        }
      );

      # To activate the default environment:
      # nix develop
      # Or if you use direnv:
      # direnv allow
      devShells = forEachSupportedSystem (
        { pkgs, ... }:
        {
          # Run `nix develop` to activate this environment or `direnv allow` if you have direnv installed
          default = import ./nix/devshells/default.nix { inherit pkgs; };
        }
      );
    };
}
