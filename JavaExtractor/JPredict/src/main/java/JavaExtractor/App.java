package JavaExtractor;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedList;
import java.util.List;
import java.util.concurrent.*;

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
			try {
				extractFeaturesTask.call();
			}
			catch (Exception e){
				e.printStackTrace();
			}
		} else if (s_CommandLineValues.Dir != null) {
			extractDir();
		}
	}

	private static void extractDir() {
		ThreadPoolExecutor executor = (ThreadPoolExecutor) Executors.newFixedThreadPool(s_CommandLineValues.NumThreads);
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
			List<Pair<Future<Void>, String>> future = new ArrayList<>();
			tasks.forEach((task) -> {
				future.add(Pair.makePair(executor.submit(task), task.filename()));
			});
			for (Pair<Future<Void>, String> f : future) {
				if (!f.first().isDone()) {
					try {
						f.first().get(s_CommandLineValues.Timeout, TimeUnit.MINUTES);
					} catch (Exception e) {
						System.err.println("ATTENTION! "+ f.second());
						f.first().cancel(true);
						e.printStackTrace();
					}
				}
			}

		} finally {
			executor.shutdown();
		}
	}
}
