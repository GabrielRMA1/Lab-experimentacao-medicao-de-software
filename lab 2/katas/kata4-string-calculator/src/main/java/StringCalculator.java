import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.regex.Pattern;

public class StringCalculator {
    public static int add(String numbers) {
        if (numbers == null || numbers.trim().isEmpty()) {
            return 0;
        }

        String input = numbers.trim();
        String delimiterPattern = "[,\\n]";

        if (input.startsWith("//")) {
            int newlineIndex = input.indexOf('\n');
            if (newlineIndex == -1) {
                throw new IllegalArgumentException("Formato de delimitador inválido");
            }

            String delimiter = input.substring(2, newlineIndex);
            input = input.substring(newlineIndex + 1);
            delimiterPattern = buildDelimiterPattern(delimiter);
        }

        List<Integer> negatives = new ArrayList<>();
        int sum = 0;

        for (String token : input.split(delimiterPattern)) {
            if (token == null || token.isEmpty()) {
                continue;
            }

            int value = Integer.parseInt(token.trim());
            if (value < 0) {
                negatives.add(value);
            }
            if (value <= 1000) {
                sum += value;
            }
        }

        if (!negatives.isEmpty()) {
            throw new IllegalArgumentException("Negatives not allowed: " + negatives);
        }

        return sum;
    }

    private static String buildDelimiterPattern(String delimiter) {
        if (delimiter.startsWith("[") && delimiter.endsWith("]")) {
            String[] values = delimiter.substring(1, delimiter.length() - 1).split("\\]\\[");
            return Arrays.stream(values)
                    .map(Pattern::quote)
                    .reduce((a, b) -> a + "|" + b)
                    .orElse(Pattern.quote(delimiter));
        }

        return Pattern.quote(delimiter);
    }
}