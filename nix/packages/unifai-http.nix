{
  pkgs,
  inputs,
  src,
  version,
  unifai-ui,
}:
let
  lib = pkgs.lib;

  # UnifAI requires Go 1.26 (go.mod/go.work). Force Go 1.26 for buildGoModule.
  buildGoModule = pkgs.callPackage "${inputs.nixpkgs}/pkgs/build-support/go/module.nix" {
    go = pkgs.go_1_26 or pkgs.go;
  };

  transportsLocalReplaces = ''
    if [ -f transports/go.mod ]; then
      cat >> transports/go.mod <<'EOF'

    replace github.com/unifai/unifai/core => ../core
    replace github.com/unifai/unifai/framework => ../framework
    replace github.com/unifai/unifai/plugins/governance => ../plugins/governance
    replace github.com/unifai/unifai/plugins/compat => ../plugins/compat
    replace github.com/unifai/unifai/plugins/logging => ../plugins/logging
    replace github.com/unifai/unifai/plugins/maxim => ../plugins/maxim
    replace github.com/unifai/unifai/plugins/otel => ../plugins/otel
    replace github.com/unifai/unifai/plugins/semanticcache => ../plugins/semanticcache
    replace github.com/unifai/unifai/plugins/telemetry => ../plugins/telemetry
    EOF
    fi
  '';
in
buildGoModule {
  pname = "unifai-http";
  inherit version;
  inherit src;

  modRoot = "transports";
  subPackages = [ "unifai-http" ];
  vendorHash = "sha256-Ck1cwv/DYI9EXmp7U2ZSNXlU+Qok8BFn5bcN1Pv7Nmc=";

  doCheck = false;

  overrideModAttrs = final: prev: {
    postPatch = (prev.postPatch or "") + transportsLocalReplaces;
  };

  env = {
    CGO_ENABLED = "1";
  };

  nativeBuildInputs = with pkgs; [
    pkg-config
    gcc
  ];
  buildInputs = [ pkgs.sqlite ];

  postPatch = transportsLocalReplaces;

  preBuild = ''
    # Provide UI assets for //go:embed all:ui
    rm -rf unifai-http/ui
    mkdir -p unifai-http/ui
    if [ -d "${unifai-ui}/ui" ]; then
      cp -R --no-preserve=mode,ownership,timestamps "${unifai-ui}/ui/." unifai-http/ui/
    else
      printf '%s\n' '<!doctype html><meta charset="utf-8"><title>UnifAI</title>' > unifai-http/ui/index.html
    fi
  '';

  ldflags = [
    "-s"
    "-w"
    "-X main.Version=${version}"
  ];

  meta = {
    mainProgram = "unifai-http";
    description = "UnifAI HTTP gateway";
    homepage = "https://github.com/unifai/unifai";
    license = lib.licenses.asl20;
  };
}