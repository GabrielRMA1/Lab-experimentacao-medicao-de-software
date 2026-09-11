public class BowlingGame {
    private static final int MAX_FRAMES = 10;
    private static final int MAX_ROLLS = 21;
    private final int[] rolls = new int[MAX_ROLLS];
    private int currentRoll = 0;

    public void roll(int pins) {
        if (pins < 0 || pins > 10) {
            throw new IllegalArgumentException("Pins inválidos: " + pins);
        }
        if (currentRoll >= MAX_ROLLS) {
            throw new IllegalStateException("Jogo já está completo");
        }
        rolls[currentRoll++] = pins;
    }

    public int score() {
        int total = 0;
        int index = 0;

        for (int frame = 0; frame < MAX_FRAMES; frame++) {
            if (index >= currentRoll) {
                break;
            }

            if (isStrike(index)) {
                total += 10 + nextTwoBallsForStrike(index);
                index++;
            } else {
                int first = rolls[index];
                int second = rolls[index + 1];
                int frameScore = first + second;

                if (frameScore == 10) {
                    total += 10 + nextBall(index + 2);
                } else {
                    total += frameScore;
                }
                index += 2;
            }
        }

        return total;
    }

    private boolean isStrike(int index) {
        return rolls[index] == 10;
    }

    private int nextTwoBallsForStrike(int index) {
        int total = 0;
        for (int i = 1; i <= 2 && index + i < currentRoll; i++) {
            total += rolls[index + i];
        }
        return total;
    }

    private int nextBall(int index) {
        return index < currentRoll ? rolls[index] : 0;
    }
}