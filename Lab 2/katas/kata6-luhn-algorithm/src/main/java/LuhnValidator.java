public class LuhnValidator {
    public static boolean isValid(String cardNumber) {
        if (cardNumber == null) {
            return false;
        }

        String digits = cardNumber.replaceAll("\\s+", "");
        if (digits.isEmpty() || !digits.matches("\\d+")) {
            return false;
        }

        int sum = 0;
        boolean doubleNext = false;

        for (int i = digits.length() - 1; i >= 0; i--) {
            int value = Character.getNumericValue(digits.charAt(i));

            if (doubleNext) {
                value *= 2;
                if (value > 9) {
                    value -= 9;
                }
            }

            sum += value;
            doubleNext = !doubleNext;
        }

        return sum % 10 == 0;
    }
}