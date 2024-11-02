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
        propagatedBuildInputs = with pkgs.python312Packages; [
          cryptography
          keyring
        ];
        pycookiecheat =
          { lib, python312 }:
          python312.pkgs.buildPythonPackage {
            inherit pname;
            version = builtins.elemAt (lib.splitString "\"" (
              lib.findSingle (val: builtins.match "^__version__ = \".*\"$" val != null) (abort "none")
                (abort "multiple")
                (lib.splitString "\n" (builtins.readFile ./src/pycookiecheat/__init__.py))
            )) 1;

            src = lib.cleanSource ./.;
            pyproject = true;
            nativeBuildInputs = with pkgs.python312Packages; [ setuptools-scm ];
            inherit propagatedBuildInputs;
          };
      in
      {
        packages = {
          ${pname} = pkgs.callPackage pycookiecheat { };
          default = pkgs.python312.withPackages (_: [ self.packages.${system}.${pname} ]);
        };

        devShells.default = pkgs.mkShell {
          venvDir = ".venv";
          postVenvCreation = ''
            unset SOURCE_DATE_EPOCH
            pip install -e .[dev,test]
            python -m playwright install chromium firefox
          '';
          buildInputs = with pkgs; [
            python39
            python310
            python311
            python313

            python312Packages.venvShellHook
            (python312.withPackages (ps: [ ps.tox ]))
          ];
        };

        apps.default = {
          type = "app";
          program = "${self.outputs.packages.${system}.pycookiecheat}/bin/pycookiecheat";
        };
      }
    );
}
