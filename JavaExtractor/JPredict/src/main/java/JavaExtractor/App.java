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
			List<Future<Void>> future = new ArrayList<>();
			tasks.forEach((task) -> {
				future.add(executor.submit(task));
			});
			for (Future<Void> f : future) {
				if (!f.isDone()) {
					try {
						f.get(s_CommandLineValues.Timeout, TimeUnit.MINUTES);
					} catch (Exception e) {
						System.err.println("ATTENTION! "+ f);
						f.cancel(true);
						e.printStackTrace();
						System.out.println(new Date());
					}
				}
			}

		} finally {
			executor.shutdown();
		}
	}
}
