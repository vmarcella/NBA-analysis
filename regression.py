"""
    Module for handling all linear regressions to be performed on our
    dataset
"""
import logging
from collections import namedtuple

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from data import get_nba_df, get_train_test
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler, StandardScaler

LOG_FORMAT = "%(name)s - %(levelname)s - \t%(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)


def filter_cols(dataframe: pd.DataFrame) -> tuple:
    """
        Filter unwanted columns from our nba dataframe for our linear regression model

        Args:
            df -> The nba dataframe

        Returns:
            tuple containing (nba player stats, nba player win shares)
    """
    # Columns we want to remove
    unwanted_cols = [
        "Unnamed: 0",
        "Year",
        "Player",
        "Pos",
        "Age",
        "Tm",
        "blanl",
        "blank2",
        "OWS",
        "DWS",
        "WS",
        "WS/48",
        "PER",
        "BPM",
        "OBPM",
        "DBPM",
        "eFG%",
        "TOV",
        "TS%",
        "3PAr",
        "VORP",
        "FTr",
        "ORB%",
        "DRB%",
        "TRB%",
        "AST%",
        "STL%",
        "BLK%",
        "TOV%",
        "USG%",
    ]

    # Target column we'd like
    target_col = ["WS"]

    # Grab the nba stats
    nba_stats = dataframe.drop(columns=unwanted_cols)
    nba_ws = dataframe[target_col]
    return nba_stats, nba_ws


def apply_pca(
    dataframe: pd.DataFrame, dimensions: int = 0, threshold: float = 0.95
) -> pd.DataFrame:
    """
        Apply pca to our nba dataframe given the dimensionality
        we tend to reduce to

        Args:
            df -> The nba dataframe
            dimensions -> The dimensions we tend to reduce to (if 0, auto detect based on our threshold)
            threshold -> The threshold for information preserved by our pca model.
                         Needed for determining the best number of dimensions

        Returns:
            PCA scaled dataframe

    """
    pca = None
    components = None
    info_preserved = 0

    if dimensions:
        pca = PCA(n_components=dimensions)
        components = pca.fit_transform(dataframe)
        # Grab the total information preserved by the dimension we're using
        info_preserved = pca.explained_variance_ratio_.cumsum()[-1] * 100
    else:
        logging.debug(
            f"  - No dimensions provided, finding a dimension that preserves {threshold * 100}% of the original information"
        )
        info_preserved = 0
        while info_preserved < threshold:
            dimensions += 1
            logging.debug(f"  - Reducing our model to {dimensions} dimensions")
            pca = PCA(n_components=dimensions)
            components = pca.fit_transform(dataframe)
            info_preserved = pca.explained_variance_ratio_.cumsum()[-1]

    logging.debug(
        f"  - PCA preserved {info_preserved * 100:.2f}% information with {dimensions} reduced dimensions"
    )
    # Construct our new pca dataframe
    pca_df = pd.DataFrame(
        data=components, columns=["pca-" + str(x + 1) for x in range(dimensions)]
    )
    return pca_df


def apply_scaling(features: pd.DataFrame, scale_type: str = "Standard") -> pd.DataFrame:
    """
        apply scaling to our dataframe

        Args:
            features -> the dataframe containing player stats/features
            scale_type -> the type of scaling that we'd like to apply our data

        Returns:
            The scaled dataframe
    """
    scaled_features = features
    if scale_type == "Standard":
        std_scaler = StandardScaler()
        std_features = std_scaler.fit_transform(features)
        scaled_features = pd.DataFrame(std_features, columns=scaled_features.columns)

    elif scale_type == "MinMax":
        mm_scaler = MinMaxScaler()
        mm_features = mm_scaler.fit_transform(features)
        scaled_features = pd.DataFrame(mm_features, columns=scaled_features.columns)

    return scaled_features


def create_linear_regression(
    features: namedtuple, target: namedtuple
) -> LinearRegression:
    """
        Create the linear regression model

        Args:
            training_data -> tuple of both training X and Y data
            testing_data -> tuple of both testing X and Y data

        Returns:
            Linear regression model
    """
    reg_model = LinearRegression()
    reg_model.fit(features.training, target.training)
    model_r2_score = reg_model.score(features.testing, target.testing)

    # Get model scores
    prediction = reg_model.predict(features.testing)
    sk_r2_score = r2_score(target.testing, prediction)
    mean_sqrd_err = mean_squared_error(target.testing, prediction)

    logging.debug(f"Model predicted r2 score: {model_r2_score}")
    logging.debug(f"Sklearn predicted r2 score: {sk_r2_score}")
    logging.debug(f"Mean squared error: {mean_sqrd_err}")
    return reg_model


# The available model types we can use for linear regression
MODELTYPES = {
    1: "standard",
    2: "stdscaled",
    3: "mmscaled",
    4: "pca",
    5: "stdpca",
    6: "mmpca",
}


def obtain_linear_reg(
    model_type: int = 0,
    pca_dimensions: int = 3,
    pca_threshold: float = 0.95,
    from_year: int = 2010,
    to_year: int = 2018,
) -> LinearRegression:
    """
        Obtain a linear regression model

        Args:
            model_type -> the type of model data we'd like to build our regression with
            pca_dimensions -> the number of dimensions to apply to pca (if 0, auto-detect the dimensions)
            pca_threshold -> The threshold for information preserved by our pca models 
            from_year -> the year we want our nba data to be selected from
            to_year -> the year we want our nba data up to

        Returns:
            Linear regression model using our customized nba dataset
    """
    logging.debug("----OBTAINING NEW REGRESSION MODEL----")
    nba_stats, nba_ws = filter_cols(get_nba_df(from_year=from_year, to_year=to_year))
    nba_stats = nba_stats.fillna(0)

    # The model we'd like
    scaling = MODELTYPES.get(model_type, "no scaling")

    logging.debug(f"Applying {scaling} to our data")
    # obtain correct data
    if scaling == "stdscaled":
        nba_stats = apply_scaling(nba_stats)
    elif scaling == "mmscaled":
        nba_stats = apply_scaling(nba_stats)
    elif scaling == "pca":
        nba_stats = apply_pca(nba_stats, pca_dimensions, pca_threshold)
    elif scaling == "stdpca":
        nba_stats = apply_pca(apply_scaling(nba_stats), pca_dimensions, pca_threshold)
    elif scaling == "mmpca":
        nba_stats = apply_pca(apply_scaling(nba_stats), pca_dimensions, pca_threshold)

    # Obtain features and target data
    features, target = get_train_test(nba_stats, nba_ws)

    logging.debug(
        f"Creating linear regression model comprised of {len(nba_stats.columns)} features"
    )
    reg_model = create_linear_regression(features, target)

    logging.debug("----FINISHED OBTAINING REGRESSION MODEL----\n")

    return reg_model


def main() -> None:
    """
        Main functionality of our linear regression
    """
    # Gather the necessary features
    nba_stats, nba_ws = filter_cols(get_nba_df(from_year=2000))
    nba_pca = apply_pca(nba_stats.fillna(0), dimensions=5)
    std_nba = apply_scaling(nba_stats.fillna(0))
    mm_nba = apply_scaling(nba_stats.fillna(0), scale_type="MinMax")
    std_pca = apply_scaling(nba_pca)
    mm_pca = apply_scaling(nba_pca, scale_type="MinMax")

    # get train testing data
    features, target = get_train_test(nba_stats.fillna(0), nba_ws)
    pca_feats, pca_target = get_train_test(nba_pca, nba_ws)
    std_features, std_target = get_train_test(std_nba, nba_ws)
    mm_features, mm_target = get_train_test(mm_nba, nba_ws)
    std_pca, std_pca_target = get_train_test(std_pca, nba_ws)
    mm_pca, mm_pca_target = get_train_test(mm_pca, nba_ws)

    # Create linear regression models

    # create_linear_regression(features, target)
    # create_linear_regression(pca_feats, pca_target)
    # create_linear_regression(std_features, std_target)
    # create_linear_regression(mm_features, mm_target)
    # create_linear_regression(std_pca, std_pca_target)
    # create_linear_regression(mm_pca, mm_pca_target)
    obtain_linear_reg()
    # Find number of dimensions that preserves 95% of the information from our original model
    obtain_linear_reg(model_type=4, pca_dimensions=0, pca_threshold=0.95)


if __name__ == "__main__":
    main()
