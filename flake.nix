{
  description = "Flake for https://github.com/n8henrie/pycookiecheat";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "aarch64-darwin"
        "aarch64-linux"
        "x86_64-darwin"
        "x86_64-linux"
      ];
      eachSystem =
        with nixpkgs.lib;
        f: foldAttrs mergeAttrs { } (map (s: mapAttrs (_: v: { ${s} = v; }) (f s)) systems);
    in
    eachSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        pname = "pycookiecheat";
        propagatedBuildInputs = with pkgs.python311Packages; [
          cryptography
          keyring
        ];
        pycookiecheat =
          { lib, python311 }:
          python311.pkgs.buildPythonPackage {
            inherit pname;
            version = builtins.elemAt (lib.splitString "\"" (
              lib.findSingle (val: builtins.match "^__version__ = \".*\"$" val != null) (abort "none")
                (abort "multiple")
                (lib.splitString "\n" (builtins.readFile ./src/pycookiecheat/__init__.py))
            )) 1;

            src = lib.cleanSource ./.;
            pyproject = true;
            nativeBuildInputs = with pkgs.python311Packages; [ setuptools-scm ];
            inherit propagatedBuildInputs;
          };
      in
      {
        packages = {
          ${pname} = pkgs.callPackage pycookiecheat { };
          default = pkgs.python311.withPackages (_: [ self.packages.${system}.${pname} ]);
        };

        devShells.default = pkgs.mkShell {
          venvDir = ".venv";
          postVenvCreation = ''
            unset SOURCE_DATE_EPOCH
            pip install -e .[dev,test]
            python -m playwright install chromium firefox
          '';
          buildInputs = with pkgs; [
            (python39.withPackages (ps: [ ]))
            (python310.withPackages (ps: [ ]))
            (python311.withPackages (ps: [ ]))
            (python312.withPackages (ps: [ ]))
            python313Packages.venvShellHook
            (python313.withPackages (ps: [ ps.tox ]))
          ];
        };

        apps.default = {
          type = "app";
          program = "${self.outputs.packages.${system}.pycookiecheat}/bin/pycookiecheat";
        };
      }
    );
}
