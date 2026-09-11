public class RomanNumerals {
    private static final int[] VALUES = {1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1};
    private static final String[] SYMBOLS = {"M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"};

    public static String convert(int number) {
        if (number < 1 || number > 3999) {
            throw new IllegalArgumentException("Número fora do intervalo suportado: 1 a 3999");
        }

        StringBuilder result = new StringBuilder();
        int remainder = number;

        for (int i = 0; i < VALUES.length && remainder > 0; i++) {
            while (remainder >= VALUES[i]) {
                result.append(SYMBOLS[i]);
                remainder -= VALUES[i];
            }
        }

        return result.toString();
    }
}