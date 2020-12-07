package JavaExtractor.Common;

import com.github.javaparser.ast.Node;
import spoon.reflect.declaration.CtMethod;

import java.util.ArrayList;

public class MethodContent {
  private ArrayList<Node> leaves;
  private String name;
  private long length;
  private String method;
  public MethodContent(ArrayList<Node> leaves, String name, long length, String method) {
    this.leaves = leaves;
    this.name = name;
    this.length = length;
    this.method = method;
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

  public String getMethodName(){return method;}
}
