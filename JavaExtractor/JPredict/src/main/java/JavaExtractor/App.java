package JavaExtractor;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedList;
import java.util.List;
import java.util.concurrent.*;

import JavaExtractor.Common.TimeoutCaller;
import org.kohsuke.args4j.CmdLineException;

import JavaExtractor.Common.CommandLineValues;
import JavaExtractor.FeaturesEntities.ProgramRelation;
import JavaExtractor.Common.Pair;

public class App {
    private static CommandLineValues s_CommandLineValues;

    public static void main(String[] args) {
        try {
            s_CommandLineValues = new CommandLineValues(args);
        } catch (CmdLineException e) {
            e.printStackTrace();
            return;
        }

        if (s_CommandLineValues.NoHash) {
            ProgramRelation.setNoHash();
        }

        if (s_CommandLineValues.File != null) {
            ExtractFeaturesTask extractFeaturesTask = new ExtractFeaturesTask(s_CommandLineValues,
                    s_CommandLineValues.File.toPath());
            extractFeaturesTask.run();

        } else if (s_CommandLineValues.Dir != null) {
            extractDir();
        }
    }

    private static void extractDir() {
        ThreadPoolExecutor executor = (ThreadPoolExecutor) Executors.newFixedThreadPool(s_CommandLineValues.NumThreads);
        executor.setMaximumPoolSize(s_CommandLineValues.NumThreads + 2);
        LinkedList<ExtractFeaturesTask> tasks = new LinkedList<>();
        try {
            Files.walk(Paths.get(s_CommandLineValues.Dir)).filter(Files::isRegularFile)
                    .filter(p -> p.toString().toLowerCase().endsWith(".java")).forEach(f -> {
                ExtractFeaturesTask task = new ExtractFeaturesTask(s_CommandLineValues, f);
                tasks.add(task);
            });
        } catch (IOException e) {
            e.printStackTrace();
            return;
        }
        try {
            for (ExtractFeaturesTask task : tasks) {
                while (executor.getTaskCount() - executor.getCompletedTaskCount() > 8) {
                } // prevent from creating a lot of threads in memory.
                System.err.println(executor.getActiveCount() + " Total:" + executor.getTaskCount() + " Compl." + executor.getCompletedTaskCount() + " IN QUEUE:" + (executor.getTaskCount() - executor.getCompletedTaskCount()));
                executor.execute(new TimeoutCaller(task, s_CommandLineValues.Timeout * 10, task.filename()));
            }
        } finally {
            executor.shutdown();
        }
    }
}
