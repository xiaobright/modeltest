#include <string.h>
void add_vectors(double *v1, double *v2, int size, double *result) {
    for(int i = 0; i < size; ++i)
        result[i] = v1[i] + v2[i];
}
void mul_vector_number(double *v1, double num, int size, double *result) {
    for(int i = 0; i < size; ++i)
        result[i] = v1[i] * num;
}
void score(double * input, double * output) {
    double var0[3];
    double var1[3];
    double var2[3];
    double var3[3];
    double var4[3];
    double var5[3];
    double var6[3];
    double var7[3];
    double var8[3];
    double var9[3];
    double var10[3];
    if (input[1578] <= 0.4686274528503418) {
        memcpy(var10, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
    } else {
        if (input[1916] <= 0.4960784316062927) {
            memcpy(var10, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
        } else {
            if (input[2956] <= 25.19801139831543) {
                if (input[2020] <= 0.4313725531101227) {
                    memcpy(var10, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
                } else {
                    if (input[2802] <= 27.260774612426758) {
                        memcpy(var10, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
                    } else {
                        if (input[440] <= 0.6294117867946625) {
                            memcpy(var10, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
                        } else {
                            memcpy(var10, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
                        }
                    }
                }
            } else {
                if (input[2057] <= 28.054428100585938) {
                    memcpy(var10, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
                } else {
                    memcpy(var10, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
                }
            }
        }
    }
    double var11[3];
    if (input[1943] <= 0.4647058844566345) {
        if (input[292] <= 0.9862745106220245) {
            memcpy(var11, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
        } else {
            if (input[3074] <= 17.084749221801758) {
                memcpy(var11, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            } else {
                memcpy(var11, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
            }
        }
    } else {
        if (input[141] <= 0.9803921580314636) {
            memcpy(var11, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
        } else {
            if (input[266] <= 0.7686274647712708) {
                if (input[3307] <= 23.423551559448242) {
                    memcpy(var11, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
                } else {
                    memcpy(var11, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
                }
            } else {
                memcpy(var11, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            }
        }
    }
    add_vectors(var10, var11, 3, var9);
    double var12[3];
    if (input[1972] <= 0.45686274766921997) {
        if (input[462] <= 0.4882352948188782) {
            memcpy(var12, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
        } else {
            if (input[1256] <= 0.8470588326454163) {
                if (input[100] <= 0.9705882370471954) {
                    memcpy(var12, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
                } else {
                    memcpy(var12, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
                }
            } else {
                memcpy(var12, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
            }
        }
    } else {
        if (input[3253] <= 30.048847198486328) {
            memcpy(var12, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
        } else {
            if (input[1222] <= 0.9470588266849518) {
                memcpy(var12, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            } else {
                memcpy(var12, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
            }
        }
    }
    add_vectors(var9, var12, 3, var8);
    double var13[3];
    if (input[1480] <= 0.4843137264251709) {
        memcpy(var13, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
    } else {
        if (input[1383] <= 0.6901960968971252) {
            if (input[984] <= 0.45686274766921997) {
                if (input[524] <= 0.45686274766921997) {
                    memcpy(var13, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
                } else {
                    memcpy(var13, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
                }
            } else {
                memcpy(var13, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            }
        } else {
            if (input[3403] <= 24.186052322387695) {
                memcpy(var13, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
            } else {
                memcpy(var13, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            }
        }
    }
    add_vectors(var8, var13, 3, var7);
    double var14[3];
    if (input[1544] <= 0.4803921580314636) {
        if (input[339] <= 0.5039215832948685) {
            memcpy(var14, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
        } else {
            memcpy(var14, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
        }
    } else {
        if (input[636] <= 0.821568638086319) {
            memcpy(var14, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
        } else {
            if (input[829] <= 0.5529412031173706) {
                memcpy(var14, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
            } else {
                if (input[2747] <= 20.06938362121582) {
                    memcpy(var14, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
                } else {
                    if (input[296] <= 0.5843137502670288) {
                        memcpy(var14, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
                    } else {
                        memcpy(var14, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
                    }
                }
            }
        }
    }
    add_vectors(var7, var14, 3, var6);
    double var15[3];
    if (input[2009] <= 0.4490196108818054) {
        if (input[2319] <= 29.33211898803711) {
            memcpy(var15, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
        } else {
            if (input[518] <= 0.6137255132198334) {
                memcpy(var15, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
            } else {
                memcpy(var15, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            }
        }
    } else {
        if (input[1112] <= 0.8666666746139526) {
            memcpy(var15, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
        } else {
            if (input[1464] <= 0.594117671251297) {
                memcpy(var15, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
            } else {
                if (input[2391] <= 20.764678955078125) {
                    memcpy(var15, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
                } else {
                    if (input[2036] <= 0.44509804248809814) {
                        memcpy(var15, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
                    } else {
                        memcpy(var15, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
                    }
                }
            }
        }
    }
    add_vectors(var6, var15, 3, var5);
    double var16[3];
    if (input[951] <= 0.4647058844566345) {
        if (input[361] <= 0.6843137443065643) {
            if (input[2290] <= 23.544559478759766) {
                memcpy(var16, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            } else {
                memcpy(var16, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
            }
        } else {
            memcpy(var16, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
        }
    } else {
        if (input[1238] <= 0.8294117748737335) {
            if (input[1427] <= 0.5882353186607361) {
                memcpy(var16, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            } else {
                memcpy(var16, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
            }
        } else {
            if (input[1418] <= 0.345098040997982) {
                memcpy(var16, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
            } else {
                memcpy(var16, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            }
        }
    }
    add_vectors(var5, var16, 3, var4);
    double var17[3];
    if (input[1914] <= 0.4882352948188782) {
        if (input[392] <= 0.6529411971569061) {
            memcpy(var17, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
        } else {
            if (input[1222] <= 0.864705890417099) {
                memcpy(var17, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            } else {
                memcpy(var17, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
            }
        }
    } else {
        if (input[144] <= 0.9843137264251709) {
            if (input[1353] <= 0.4725490212440491) {
                memcpy(var17, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
            } else {
                memcpy(var17, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            }
        } else {
            if (input[501] <= 0.5039215832948685) {
                if (input[1205] <= 0.8568627536296844) {
                    memcpy(var17, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
                } else {
                    memcpy(var17, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
                }
            } else {
                memcpy(var17, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
            }
        }
    }
    add_vectors(var4, var17, 3, var3);
    double var18[3];
    if (input[2007] <= 0.4529411792755127) {
        if (input[3514] <= 25.366430282592773) {
            if (input[2035] <= 0.44117647409439087) {
                if (input[1454] <= 0.5098039507865906) {
                    memcpy(var18, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
                } else {
                    memcpy(var18, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
                }
            } else {
                memcpy(var18, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            }
        } else {
            if (input[2520] <= 23.788509368896484) {
                memcpy(var18, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            } else {
                memcpy(var18, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
            }
        }
    } else {
        if (input[891] <= 0.5529412031173706) {
            if (input[1651] <= 0.5039215981960297) {
                memcpy(var18, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
            } else {
                if (input[3795] <= 24.559667587280273) {
                    memcpy(var18, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
                } else {
                    memcpy(var18, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
                }
            }
        } else {
            memcpy(var18, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
        }
    }
    add_vectors(var3, var18, 3, var2);
    double var19[3];
    if (input[1029] <= 0.9392156898975372) {
        if (input[3654] <= 27.66096305847168) {
            memcpy(var19, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
        } else {
            memcpy(var19, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
        }
    } else {
        if (input[1756] <= 0.5274510085582733) {
            memcpy(var19, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
        } else {
            if (input[1480] <= 0.4843137264251709) {
                if (input[100] <= 0.9921568632125854) {
                    memcpy(var19, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
                } else {
                    memcpy(var19, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
                }
            } else {
                if (input[1266] <= 0.800000011920929) {
                    if (input[1940] <= 0.4647058844566345) {
                        memcpy(var19, (double[]){0.0, 0.0, 1.0}, 3 * sizeof(double));
                    } else {
                        memcpy(var19, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
                    }
                } else {
                    if (input[2580] <= 24.802791595458984) {
                        memcpy(var19, (double[]){0.0, 1.0, 0.0}, 3 * sizeof(double));
                    } else {
                        memcpy(var19, (double[]){1.0, 0.0, 0.0}, 3 * sizeof(double));
                    }
                }
            }
        }
    }
    add_vectors(var2, var19, 3, var1);
    mul_vector_number(var1, 0.1, 3, var0);
    memcpy(output, var0, 3 * sizeof(double));
}
