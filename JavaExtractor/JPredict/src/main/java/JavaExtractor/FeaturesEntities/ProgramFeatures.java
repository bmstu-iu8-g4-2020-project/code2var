package JavaExtractor.FeaturesEntities;

import JavaExtractor.Common.CommandLineValues;
import JavaExtractor.Common.Common;
import com.fasterxml.jackson.annotation.JsonIgnore;

import java.util.ArrayList;
import java.util.stream.Collectors;

public class ProgramFeatures {
  private CommandLineValues m_CommandLineValues;

  private String name;
  private String normalizedName;
  private String methodName; // For code2var name != methodName
  private ArrayList<ProgramRelation> features = new ArrayList<>();

  public ProgramFeatures(String name, CommandLineValues commandLineValues, String methodName) {
    this.name = name;
    this.normalizedName = Common.normalizeName(name, Common.BlankWord);
    this.m_CommandLineValues = commandLineValues;
    this.methodName = methodName;
  }

  @SuppressWarnings("StringBufferReplaceableByString")
  @Override
  public String toString() {
    StringBuilder stringBuilder = new StringBuilder();
    stringBuilder.append(name).append(" ");
    stringBuilder.append(
        features.stream().map(ProgramRelation::toString).collect(Collectors.joining(" ")));

    return stringBuilder.toString();
  }

  public void addFeature(String source, String path, String target) {
    if (m_CommandLineValues.OnlyVars && source.equals(this.name)) {
      source = Common.variableName;
    }
    if (m_CommandLineValues.OnlyVars && target.equals(this.name)) {
      target = Common.variableName;
    }
    if (source.equals(this.methodName)){
      source = Common.methodName;
    }
    if (target.equals(this.methodName)){
      target = Common.methodName;
    }
    if (m_CommandLineValues.OnlyVars && source.startsWith("VAR_")){
      source = "VAR";
    }
    if (m_CommandLineValues.OnlyVars && target.startsWith("VAR_")){
      target = "VAR";
    }

    ProgramRelation newRelation = new ProgramRelation(source, target, path);
    features.add(newRelation);
  }

  @JsonIgnore
  public boolean isEmpty() {
    return features.isEmpty();
  }

  public void deleteAllPaths() {
    features.clear();
  }

  public String getName() {
    return name;
  }

  public void setName(String s) {
    name = s;
  }

  public ArrayList<ProgramRelation> getFeatures() {
    return features;
  }

  public String getMethodName() {
    return methodName;
  }
}
