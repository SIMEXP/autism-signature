# Hien Nguyen, 2019
# https://hiendn.github.io/

# Argument parsing (source fMRI directory and result directory for the validation script)
args <- commandArgs(trailingOnly = TRUE)

# Defaults if no arguments (for interactive use)
source_dir <- ifelse(length(args) >= 1, args[1], "source_data/Data")
validation_dir <- ifelse(length(args) >= 3, args[3], "output_data/Validation")
Debug.Flag <- ifelse(length(args) >= 4, args[4] == "TRUE", FALSE)
cat("💾 Reading source data from:", source_dir, "\n")
cat("💾 Writing outputs to:", validation_dir, "\n")

# Load phenotypes
phenos <- read.delim(file.path(source_dir, "ABIDE2_Pheno_PSM_matched.tsv"))
# Reduce data size for debugging
if (Debug.Flag) {
  cat("⚠️  DEBUG MODE ACTIVE: limiting phenos to 20 rows\n"); flush.console()
  phenos <- phenos[1:20, ]
}
classes_var <- ifelse(phenos$DX_GROUP == "Control", 0, 1)

# Initialize an array for the results
Results_array <- array(NA,
                       c(dim(phenos)[1],4,18))

for (Network in 1:18) {
  # Read from file
  Read_file <- read.csv(file.path(validation_dir, paste('Results_Real_Network_',Network,'.csv',sep = '')),
                        header = TRUE)

  # Store file to array
  Results_array[,,Network] <- as.matrix(Read_file[,2:5])
}

#################################################################
##                Combine p-values across Subnets              ##
#################################################################

### Subnets
Subnets_list <- list()
Subnets_list[[1]] <- 3
Subnets_list[[2]] <- 18
Subnets_list[[3]] <- c(2,7,10)
Subnets_list[[4]] <- c(1,5,9,16)
Subnets_list[[5]] <- c(4,12,13)
Subnets_list[[6]] <- c(8,14,15)
Subnets_list[[7]] <- c(6,11,1)
Subnets_list[[8]] <- 1:18
Subnets_results_list <- list()

# Declare storage matrices
Pvalue0_combine <- matrix(NA,dim(phenos)[1],8)
Pvalue1_combine <- matrix(NA,dim(phenos)[1],8)

# Loop over subnets
for (subnet in 1:8) {
    if (length(Subnets_list[[subnet]])==1) {
      Combine0_mat <- Results_array[,4,Subnets_list[[subnet]]]
      Combine1_mat <- Results_array[,3,Subnets_list[[subnet]]]
    } else {
      Combine0_mat <- apply(Results_array[,4,Subnets_list[[subnet]]]^2,
                            1,
                            mean)
      Combine1_mat <- apply(Results_array[,3,Subnets_list[[subnet]]]^2,
                            1,
                            mean)
    }
  Pvalue0_combine[,subnet] <- (2*Combine0_mat)^(1/2)
  Pvalue1_combine[,subnet] <- (2*Combine1_mat)^(1/2)
}

# Sub networks
Alpha <- 0.2
Sub_nets_1_class <- c()
Sub_nets_total <- c()
Sub_net_sensitive <- c()
Sub_net_specific <- c()
for (Network in 1:8) {
  Sub_nets_1_class[Network] <- mean(classes_var[which(Pvalue1_combine[,Network]>Alpha & Pvalue0_combine[,Network]<=Alpha)])
  Sub_nets_total[Network] <- {sum(classes_var[which(Pvalue1_combine[,Network]>Alpha & Pvalue0_combine[,Network]<=Alpha)]) +
      length(which(Pvalue1_combine[,Network]>=Alpha & Pvalue0_combine[,Network]>Alpha))}/length(Pvalue1_combine[,Network])
  Sub_net_sensitive[Network] <- sum(classes_var[which(Pvalue1_combine[,Network]>Alpha & Pvalue0_combine[,Network]<=Alpha)])/sum(classes_var)
  Sub_net_specific[Network] <- sum(1-classes_var[which(Pvalue1_combine[,Network]>=Alpha & Pvalue0_combine[,Network]>Alpha)])/sum(1-classes_var)
}


#################################################################
##                     Hierachies Accuracy                     ##
#################################################################

# Accuracy of hierachies
order_vector <- c(18,3,9,5,16,1,13,4,12,2,7,10,11,6,17,8,14,15)
Split_list <- list()
Split_list[[1]] <- c(0,9,18)
Split_list[[2]] <- c(0,9,12,18)
Split_list[[3]] <- c(0,5,9,12,18)
Split_list[[4]] <- c(0,5,6,9,12,18)
Split_list[[5]] <- c(0,5,6,9,12,15,18)
Split_list[[6]] <- c(0,1,5,6,9,12,15,18)

Split_results_list <- list()
for (spl in 1:6) {
  Split_array <- array(NA,c(dim(phenos)[1],2,spl+1))

  # Loop over subnet
  for (subnet in 1:(spl+1)) {

    # Combine Conformal
      if ((Split_list[[spl]][subnet+1]-Split_list[[spl]][subnet])==1) {
        Combine0_mat <- Results_array[,4,
                                                                order_vector[Split_list[[spl]][subnet+1]]]
        Combine1_mat <-Results_array[,3,
                                                                Split_list[[spl]][subnet+1]]
      } else {
        Combine0_mat <- apply(Results_array[,4,
                                          order_vector[(1+Split_list[[spl]][subnet]):Split_list[[spl]][subnet+1]]]^2,
                                          1,
                                          mean)
        Combine1_mat <- apply(Results_array[,3,
                                          order_vector[(1+Split_list[[spl]][subnet]):Split_list[[spl]][subnet+1]]]^2,
                                          1,
                                          mean)
      }
    Split_array[,2,subnet] <- (2*Combine0_mat)^(1/2)
    Split_array[,1,subnet] <- (2*Combine1_mat)^(1/2)
    # 📣 Construct output path
    output_file <- file.path(
      validation_dir,
      paste0("validation_net_split_", spl, "_model_", subnet, "_combined_p_values.tsv")
    )

    # 🔍 Announce to the void
    cat("📝 Writing split model output to:", output_file, "\n"); flush.console()

    # 💾 Save the results
    write.table(
      Split_array[,,subnet],
      file = output_file,
      sep = "\t"
    )
  }
  Split_results_list[[spl]] <- Split_array
}

# Save two particular models to csv
# DIM is (N_subjects x 2) with (P_label_Autism, P_label_Control).
# Split conformal outputs
output_split_model1 <- file.path(validation_dir, "validation_net_split_1_model_1_combined_p_values.tsv")
output_split_model2 <- file.path(validation_dir, "validation_net_split_1_model_2_combined_p_values.tsv")
cat("📝 Writing:", output_split_model1, "\n")
cat("📝 Writing:", output_split_model2, "\n")
write.table(Split_results_list[[1]][,,1], file=output_split_model1, sep="\t")
write.table(Split_results_list[[1]][,,2], file=output_split_model2, sep="\t")
