{
  description = "Flake for https://github.com/n8henrie/pycookiecheat";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";

  outputs = {
    self,
    nixpkgs,
  }: let
    inherit (nixpkgs) lib;
    systems = ["aarch64-darwin" "x86_64-linux" "aarch64-linux"];
    systemClosure = attrs:
      builtins.foldl'
      (acc: system:
        lib.recursiveUpdate acc (attrs system))
      {}
      systems;
  in
    systemClosure (
      system: let
        pkgs = import nixpkgs {inherit system;};
        pname = "pycookiecheat";
        propagatedBuildInputs = with pkgs.python311Packages; [
          cryptography
          keyring
        ];
        pycookiecheat = {
          lib,
          python311,
        }:
          python311.pkgs.buildPythonPackage {
            inherit pname;
            version =
              builtins.elemAt
              (lib.splitString "\""
                (lib.findSingle
                  (val: builtins.match "^__version__ = \".*\"$" val != null)
                  (abort "none")
                  (abort "multiple")
                  (lib.splitString "\n"
                    (builtins.readFile ./src/pycookiecheat/__init__.py))))
              1;

            src = lib.cleanSource ./.;
            pyproject = true;
            nativeBuildInputs = with pkgs.python311Packages; [
              setuptools-scm
            ];
            inherit propagatedBuildInputs;
          };
      in {
        packages.${system} = {
          ${pname} = pkgs.callPackage pycookiecheat {};
          default = pkgs.python311.withPackages (_: [self.packages.${system}.${pname}]);
        };

        devShells.${system}.default = pkgs.mkShell {
          buildInputs = [(pkgs.python311.withPackages (_: propagatedBuildInputs))];
        };
      }
    );
}