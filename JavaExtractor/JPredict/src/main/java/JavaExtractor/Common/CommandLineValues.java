package JavaExtractor.Common;

import org.kohsuke.args4j.CmdLineException;
import org.kohsuke.args4j.CmdLineParser;
import org.kohsuke.args4j.Option;

import java.io.File;

/** This class handles the programs arguments. */
public class CommandLineValues {
  @Option(name = "--file")
  public File File = null;

  @Option(name = "--dir", forbids = "--file")
  public String Dir = null;

  @Option(name = "--max_path_length", required = true)
  public int MaxPathLength;

  @Option(name = "--max_path_width", required = true)
  public int MaxPathWidth;

  @Option(name = "--no_hash")
  public boolean NoHash = false;

  @Option(name = "--num_threads")
  public int NumThreads = 1;

  @Option(name = "--min_code_len")
  public int MinCodeLength = 1;

  @Option(name = "--max_code_len")
  public int MaxCodeLength = 10000;

  @Option(name = "--pretty_print")
  public boolean PrettyPrint = false;

  @Option(name = "--max_child_id")
  public int MaxChildId = Integer.MAX_VALUE;

  @Option(name = "--variables")
  public boolean OnlyVars = false;

  @Option(name = "--obfuscate")
  public boolean Obfuscate = false;

  @Option(name = "--timeout")
  public int Timeout = 60;

  public CommandLineValues(String... args) throws CmdLineException {
    CmdLineParser parser = new CmdLineParser(this);
    try {
      parser.parseArgument(args);
    } catch (CmdLineException e) {
      System.err.println(e.getMessage());
      parser.printUsage(System.err);
      throw e;
    }
  }
}
