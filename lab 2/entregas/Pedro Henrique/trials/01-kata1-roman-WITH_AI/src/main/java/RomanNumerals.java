import java.util.LinkedHashMap;
import java.util.Map;

public class RomanNumerals {
    private static final Map<Integer, String> GLYPHS = new LinkedHashMap<>();

    static {
        GLYPHS.put(1000, "M");
        GLYPHS.put(900, "CM");
        GLYPHS.put(500, "D");
        GLYPHS.put(400, "CD");
        GLYPHS.put(100, "C");
        GLYPHS.put(90, "XC");
        GLYPHS.put(50, "L");
        GLYPHS.put(40, "XL");
        GLYPHS.put(10, "X");
        GLYPHS.put(9, "IX");
        GLYPHS.put(5, "V");
        GLYPHS.put(4, "IV");
        GLYPHS.put(1, "I");
    }

    public static String convert(int number) {
        validate(number);
        StringBuilder out = new StringBuilder();
        int rest = number;
        for (Map.Entry<Integer, String> glyph : GLYPHS.entrySet()) {
            rest = consume(rest, glyph.getKey(), glyph.getValue(), out);
        }
        return out.toString();
    }

    private static void validate(int number) {
        if (number < 1 || number > 3999) {
            throw new IllegalArgumentException("Intervalo suportado: 1-3999");
        }
    }

    private static int consume(int rest, int value, String symbol, StringBuilder out) {
        while (rest >= value) {
            out.append(symbol);
            rest -= value;
        }
        return rest;
    }
}
