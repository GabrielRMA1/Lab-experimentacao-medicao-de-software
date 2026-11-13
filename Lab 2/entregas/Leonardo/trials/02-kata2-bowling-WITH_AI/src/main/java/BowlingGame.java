public class BowlingGame {
    private static final int FRAMES = 10;
    private final java.util.List<Integer> pinHistory = new java.util.ArrayList<>();

    public void roll(int pins) {
        pinHistory.add(pins);
    }

    public int score() {
        int total = 0;
        int cursor = 0;
        for (int frame = 0; frame < FRAMES; frame++) {
            if (isStrike(cursor)) {
                total += 10 + bonus(cursor + 1) + bonus(cursor + 2);
                cursor += 1;
            } else if (isSpare(cursor)) {
                total += 10 + bonus(cursor + 2);
                cursor += 2;
            } else {
                total += pinsAt(cursor) + pinsAt(cursor + 1);
                cursor += 2;
            }
        }
        return total;
    }

    private boolean isStrike(int index) {
        return pinsAt(index) == 10;
    }

    private boolean isSpare(int index) {
        return pinsAt(index) + pinsAt(index + 1) == 10;
    }

    private int bonus(int index) {
        return pinsAt(index);
    }

    private int pinsAt(int index) {
        if (index < 0 || index >= pinHistory.size()) {
            return 0;
        }
        return pinHistory.get(index);
    }
}
