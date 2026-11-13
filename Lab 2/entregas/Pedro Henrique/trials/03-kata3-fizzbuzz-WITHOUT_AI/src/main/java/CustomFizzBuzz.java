import java.util.Map;

public class CustomFizzBuzz {
    public static String evaluate(int number, Map<Integer, String> rules) {
        if (rules == null) {
            return "" + number;
        }

        String combined = concatMatches(number, rules);
        if (combined.length() > 0) {
            return combined;
        }
        return "" + number;
    }

    private static String concatMatches(int number, Map<Integer, String> rules) {
        String combined = "";
        for (Map.Entry<Integer, String> entry : rules.entrySet()) {
            if (matches(number, entry.getKey())) {
                combined = combined + safe(entry.getValue());
            }
        }
        return combined;
    }

    private static boolean matches(int number, Integer divisor) {
        return divisor != null && divisor != 0 && number % divisor == 0;
    }

    private static String safe(String word) {
        return word == null ? "" : word;
    }
}
