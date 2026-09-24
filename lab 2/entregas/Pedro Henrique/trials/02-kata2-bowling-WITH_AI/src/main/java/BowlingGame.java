public class BowlingGame {
    private int[] throwsInGame = new int[21];
    private int nextThrow = 0;

    public void roll(int pins) {
        throwsInGame[nextThrow] = pins;
        nextThrow = nextThrow + 1;
    }

    public int score() {
        int score = 0;
        int t = 0;
        int frame = 1;
        while (frame <= 10) {
            if (strike(t)) {
                score = score + 10 + throwsInGame[t + 1] + throwsInGame[t + 2];
                t = t + 1;
            } else {
                int first = throwsInGame[t];
                int second = throwsInGame[t + 1];
                int framePins = first + second;
                if (framePins == 10) {
                    score = score + 10 + throwsInGame[t + 2];
                } else {
                    score = score + framePins;
                }
                t = t + 2;
            }
            frame = frame + 1;
        }
        return score;
    }

    private boolean strike(int throwIndex) {
        return throwsInGame[throwIndex] == 10;
    }
}
