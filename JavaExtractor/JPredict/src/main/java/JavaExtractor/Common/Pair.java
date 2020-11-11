package JavaExtractor.Common;

public class Pair<T, U>{
    private T first;
    private U second;

    public Pair(T first, U second) {
        this.first = first;
        this.second = second;
    }

    public T first(){
        return first;
    }

    public U second(){
        return second;

    }

    public static <T, U> Pair<T, U> makePair(T first, U second) {
        return new Pair<T, U>(first, second);
    }


}