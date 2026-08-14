{
  config,
  lib,
  pkgs,
  ...
}:
let
  inherit (lib) types;

  cfg = config.services.unifai;
  settingsFormat = pkgs.formats.json { };
in
{
  options = {
    services.unifai = {
      enable = lib.mkEnableOption "UnifAI HTTP gateway";

      package = lib.mkPackageOption pkgs "unifai-http" { };

      stateDir = lib.mkOption {
        type = types.path;
        default = "/var/lib/unifai";
        example = "/var/lib/unifai";
        description = "Application data directory (contains config.json and logs).";
      };

      host = lib.mkOption {
        type = types.str;
        default = "127.0.0.1";
        example = "0.0.0.0";
        description = "The host address which the UnifAI HTTP server listens to.";
      };

      port = lib.mkOption {
        type = types.port;
        default = 8080;
        example = 11111;
        description = "Which port the UnifAI HTTP server listens to.";
      };

      logLevel = lib.mkOption {
        type = types.enum [
          "debug"
          "info"
          "warn"
          "error"
        ];
        default = "info";
        description = "Logger level.";
      };

      logStyle = lib.mkOption {
        type = types.enum [
          "json"
          "pretty"
        ];
        default = "json";
        description = "Logger output style.";
      };

      settings = lib.mkOption {
        type = types.nullOr settingsFormat.type;
        default = null;
        description = ''
          Optional content for `config.json` under `services.unifai.stateDir`.

          If set, the file will be written on service start (overwriting any existing config.json).
          If null, UnifAI will use an existing config.json (or bootstrap from environment).
        '';
        example = {
          providers = [
            {
              name = "openai";
              enabled = true;
              keys = [
                {
                  name = "default";
                  value = "env.OPENAI_API_KEY";
                }
              ];
            }
          ];
        };
      };

      environment = lib.mkOption {
        type = types.attrsOf types.str;
        default = { };
        description = "Extra environment variables for UnifAI.";
        example = {
          OPENAI_API_KEY = "...";
        };
      };

      environmentFile = lib.mkOption {
        description = ''
          Environment file to be passed to the systemd service.
          Useful for passing secrets to the service to prevent them from being
          world-readable in the Nix store.
        '';
        type = lib.types.nullOr lib.types.path;
        default = null;
        example = "/var/lib/secrets/unifai.env";
      };

      openFirewall = lib.mkOption {
        type = types.bool;
        default = false;
        description = ''
          Whether to open the firewall for UnifAI.
          This adds `services.unifai.port` to `networking.firewall.allowedTCPPorts`.
        '';
      };

      extraArgs = lib.mkOption {
        type = types.listOf types.str;
        default = [ ];
        description = "Extra CLI arguments passed to unifai-http.";
        example = [
          "-some-flag"
          "value"
        ];
      };
    };
  };

  config = lib.mkIf cfg.enable {
    assertions =
      let
        stateDirStr = toString cfg.stateDir;
      in
      [
        {
          assertion = builtins.dirOf stateDirStr == "/var/lib";
          message = "services.unifai.stateDir must be a direct child of /var/lib (e.g. /var/lib/unifai) to work with systemd StateDirectory and DynamicUser.";
        }
      ];

    systemd.services.unifai =
      let
        stateDirStr = toString cfg.stateDir;
        stateDirName = builtins.baseNameOf stateDirStr;
        configFile =
          if cfg.settings == null then null else settingsFormat.generate "unifai-config.json" cfg.settings;
      in
      {
        description = "UnifAI AI Gateway (unifai-http)";
        wantedBy = [ "multi-user.target" ];
        after = [ "network.target" ];

        environment = cfg.environment;

        preStart = lib.optionalString (configFile != null) ''
          install -Dm600 "${configFile}" "${stateDirStr}/config.json"
        '';

        serviceConfig = {
          ExecStart = lib.concatStringsSep " " (
            [
              (lib.getExe cfg.package)
              "-host"
              cfg.host
              "-port"
              (toString cfg.port)
              "-app-dir"
              stateDirStr
              "-log-level"
              cfg.logLevel
              "-log-style"
              cfg.logStyle
            ]
            ++ cfg.extraArgs
          );

          EnvironmentFile = lib.optional (cfg.environmentFile != null) cfg.environmentFile;

          WorkingDirectory = cfg.stateDir;
          StateDirectory = stateDirName;
          RuntimeDirectory = "unifai";
          RuntimeDirectoryMode = "0755";

          PrivateTmp = true;
          DynamicUser = true;
          DevicePolicy = "closed";
          LockPersonality = true;
          PrivateUsers = true;
          ProtectHome = true;
          ProtectHostname = true;
          ProtectKernelLogs = true;
          ProtectKernelModules = true;
          ProtectKernelTunables = true;
          ProtectControlGroups = true;
          RestrictNamespaces = true;
          RestrictRealtime = true;
          SystemCallArchitectures = "native";
          UMask = "0077";
          RestrictAddressFamilies = [
            "AF_INET"
            "AF_INET6"
            "AF_UNIX"
          ];
          ProtectClock = true;
          ProtectProc = "invisible";
        };
      };

    networking.firewall = lib.mkIf cfg.openFirewall { allowedTCPPorts = [ cfg.port ]; };
  };

  meta.maintainers = [
    {
      name = "ReStranger";
      github = "ReStranger";
    }
  ];
}
