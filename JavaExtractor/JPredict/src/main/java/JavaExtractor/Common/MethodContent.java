package JavaExtractor.Common;

import com.github.javaparser.ast.Node;

import java.util.ArrayList;

public class MethodContent {
  private ArrayList<Node> leaves;
  private String name;
  private long length;

  public MethodContent(ArrayList<Node> leaves, String name, long length) {
    this.leaves = leaves;
    this.name = name;
    this.length = length;
  }

  public ArrayList<Node> getLeaves() {
    return leaves;
  }

  public String getName() {
    return name;
  }

  public long getLength() {
    return length;
  }
}
