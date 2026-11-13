import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

public class StringCalculator {
    public static int add(String numbers) {
        if (numbers == null || numbers.trim().isEmpty()) {
            return 0;
        }

        ParsedInput parsed = parse(numbers);
        List<Integer> negatives = new ArrayList<>();
        int sum = 0;

        for (String token : parsed.body.split(parsed.delimiterRegex)) {
            if (token.isBlank()) {
                continue;
            }
            int value = Integer.parseInt(token.trim());
            if (value < 0) {
                negatives.add(value);
            } else if (value <= 1000) {
                sum += value;
            }
        }

        if (!negatives.isEmpty()) {
            throw new IllegalArgumentException("Negatives not allowed: " + negatives);
        }
        return sum;
    }

    private static ParsedInput parse(String numbers) {
        if (!numbers.startsWith("//")) {
            return new ParsedInput(numbers, "[,\\n]");
        }
        int nl = numbers.indexOf('\n');
        String spec = numbers.substring(2, nl);
        String body = numbers.substring(nl + 1);
        return new ParsedInput(body, Pattern.quote(spec));
    }

    private record ParsedInput(String body, String delimiterRegex) {}
}
