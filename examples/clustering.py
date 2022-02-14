from magicclass import magicclass
from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans
import numpy as np
import matplotlib.pyplot as plt

@magicclass
class Clustering2D:
    """
    scikit-learn Kmeans clustering.
    """
    def __init__(self):
        self.data = None
        self.model = None

    def generate_sample_data(self, n_clusters:int=3, n_samples:int=100):
        """
        Generate random sample data from Gaussian Mixture model.
        """
        gmm = GaussianMixture(n_components=n_clusters)
        w = np.random.random(n_clusters)
        gmm.weights_ = w/np.sum(w)
        gmm.means_ = np.random.normal(size=(n_clusters, 2))
        # covariance matrix must be positive-deterministic
        t = np.random.normal(size=(n_clusters, 2, 2))/3
        gmm.covariances_ = np.einsum("ijk,ilk->ijl", t, t)
        self.data = gmm.sample(n_samples)[0]

    def fit(self, n_clusters:int=3):
        """
        Classify the bound data using K-means method.
        """
        self.model= KMeans(n_clusters=n_clusters)
        self.model.fit(self.data)
        self.n_clusters = n_clusters

    def plot(self):
        """
        Plot the clustering results. Data points belong to different cluster will
        be plotted in different color.
        """
        plt.figure()
        for i in range(self.n_clusters):
            d = self.data[self.model.labels_ == i, :]
            plt.scatter(d[:,0], d[:,1])
        plt.show()

if __name__ == "__main__":
    ui = Clustering2D()
    ui.show()
