{
  description = "Description for the project";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    git-hooks = {
      url = "github:cachix/git-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [ inputs.git-hooks.flakeModule ];
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
        "x86_64-darwin"
      ];
      perSystem =
        {
          config,
          pkgs,
          ...
        }:
        let
          python = rec {
            version = "3.13";
            package = pkgs."python${builtins.replaceStrings [ "." ] [ "" ] version}".withPackages (
              ps: with ps; [
                uv
                ruff
              ]
            );
          };
        in
        {
          pre-commit.settings.hooks = {
            nixfmt.enable = true;
            yamlfmt.enable = true;
            yamllint.enable = true;
            taplo.enable = true;
            ruff = {
              enable = true;
              package = python.package;
            };
          };

          devShells = {
            default =
              let
                __zed = pkgs.writers.writeJSON "settings.json" {
                  lsp.ty = {
                    binary = {
                      path = "${pkgs.ty}/bin/ty";
                      arguments = [ "server" ];
                    };
                  };
                  languages.Python = {
                    language_servers = [
                      "ty"
                      "!pylsp"
                      "!pyright"
                      "!basedpyright"
                    ];
                    formatter.external = {
                      command = "${python.package}/bin/ruff";
                      arguments = [
                        "format"
                        "--stdin-filename"
                        "{buffer_path}"
                        "-"
                      ];
                    };
                  };
                };
              in
              pkgs.mkShell {
                packages =
                  with pkgs;
                  [
                    nil
                    nixd
                    nixfmt
                    go-task
                  ]
                  ++ config.pre-commit.settings.enabledPackages;

                buildInputs = with pkgs; [
                  ty
                  python.package
                ];

                shellHook = ''
                  mkdir -p .zed
                  ln -sf ${__zed} .zed/settings.json
                  ${config.pre-commit.shellHook}
                '';
              };

            ci = pkgs.mkShell {
              packages =
                with pkgs;
                [
                  go-task
                ]
                ++ config.pre-commit.settings.enabledPackages;
              buildInputs = with pkgs; [
                ty
                python.package
              ];
              shellHook = ''
                ${config.pre-commit.shellHook}
              '';
            };
          };
        };
    };
}
