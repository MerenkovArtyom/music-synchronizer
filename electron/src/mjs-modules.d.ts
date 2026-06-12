declare module "*.mjs" {
  export const buildLauncherScript: (options: {
    appPath: string;
    pythonBinaryPath: string;
    pythonHomePath: string;
    sitePackagesPath: string;
  }) => string;

  export const buildPackagedBackendLayout: (pythonVersion: string) => {
    appPath: string;
    launcherPath: string;
    pythonFrameworkPath: string;
    pythonHomePath: string;
    pythonBinaryPath: string;
    pythonVersion: string;
    sitePackagesPath: string;
  };

  export const listPrunedPythonRuntimePaths: (pythonVersion: string) => string[];
}
