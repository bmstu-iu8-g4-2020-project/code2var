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
  private ArrayList<ProgramRelation> features = new ArrayList<>();

  public ProgramFeatures(String name, CommandLineValues commandLineValues) {
    this.name = name;
    this.normalizedName = Common.normalizeName(name, Common.BlankWord);
    this.m_CommandLineValues = commandLineValues;
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

  public void addFeature(Property source, String path, Property target) {
    String sourceName = source.getName();
    String targetName = target.getName();
    if (m_CommandLineValues.OnlyVars && source.getName().equals(this.normalizedName)) {
      sourceName = Common.variableName;
    }
    if (m_CommandLineValues.OnlyVars && target.getName().equals(this.normalizedName)) {
      targetName = Common.variableName;
    }
    ProgramRelation newRelation = new ProgramRelation(sourceName, targetName, path);
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
}
