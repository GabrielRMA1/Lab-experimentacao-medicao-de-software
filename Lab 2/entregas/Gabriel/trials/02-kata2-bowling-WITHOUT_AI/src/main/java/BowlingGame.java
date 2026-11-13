public class BowlingGame {
    private final int[] rolls = new int[21];
    private int currentRoll = 0;

    public void roll(int pins) {
        if (pins < 0 || pins > 10) {
            throw new IllegalArgumentException("Jogada inválida: " + pins);
        }
        rolls[currentRoll++] = pins;
    }

    public int score() {
        int total = 0;
        int i = 0;
        for (int frame = 0; frame < 10; frame++) {
            if (rolls[i] == 10) {
                total += 10 + rolls[i + 1] + rolls[i + 2];
                i += 1;
            } else if (rolls[i] + rolls[i + 1] == 10) {
                total += 10 + rolls[i + 2];
                i += 2;
            } else {
                total += rolls[i] + rolls[i + 1];
                i += 2;
            }
        }
        return total;
    }
}
