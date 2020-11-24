package JavaExtractor.FeaturesEntities;

import JavaExtractor.Common.Common;

import java.io.UnsupportedEncodingException;
import java.net.URLEncoder;

public class ProgramNode {
  public int Id;
  public String Type;
  public String Name;
  public boolean IsMethodDeclarationName;

  public ProgramNode(String name) {
    Name = name;
    try {
      Name = URLEncoder.encode(name, Common.UTF8);
    } catch (UnsupportedEncodingException e) {
      e.printStackTrace();
    }
  }
}
