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
        pycookiecheat = {
          lib,
          python311,
          fetchPypi,
        }:
          python311.pkgs.buildPythonApplication {
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
            format = "pyproject";
            nativeBuildInputs = with pkgs.python311Packages; [
              setuptools-scm
            ];
            propagatedBuildInputs = with pkgs.python311Packages; [
              cryptography
              keyring
            ];
          };
      in {
        packages.${system} = {
          default = self.packages.${system}.${pname};
          ${pname} = pkgs.callPackage pycookiecheat {};
        };

        devShells.${system}.default = pkgs.mkShell {
          buildInputs = [pkgs.python311];
        };
      }
    );
}
