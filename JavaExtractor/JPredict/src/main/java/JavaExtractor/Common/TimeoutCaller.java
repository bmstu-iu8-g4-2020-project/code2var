package JavaExtractor.Common;

import java.util.Date;
import java.util.Timer;
import java.util.TimerTask;
import java.util.concurrent.Callable;

public class TimeoutCaller implements Runnable {
    Thread thread;
    long timeout;
    String func_name;

    public TimeoutCaller(Runnable func, long timeout, String name) {
        this.thread = new Thread(func);
        this.timeout = timeout * 1000;
        this.func_name = name;
    }

    @Override
    public void run() {
        System.err.println("Invoked timer for " + func_name + " " + "thread:" + Thread.currentThread().getId());
        new Timer(true).schedule(new TimerTask() {
            @Override
            public void run() {
                if (thread.isAlive()) {
                    thread.interrupt();
                    System.err.println("ATTENTION! Exceeded timer for " + func_name + " " + "thread:" + Thread.currentThread().getId());
                }
            }
        }, timeout * 1000);
        thread.start();
        System.err.println("Closed timer for " + func_name + " " + "thread:" + Thread.currentThread().getId());
    }


}