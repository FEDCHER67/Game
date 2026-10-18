// Generated graph functions extracted from MatrixRex Uber Stylized Water.
// MIT Copyright (c) 2025 MatrixRex. See LICENSE.
// Upstream commit: 1fdd16c6312611fef7fb248dee86cdd3fd456a1e
// G14 v02: two normal UV temporaries promoted half2 -> float2 for kilometre-scale maps.
// Otherwise unchanged; only the dependency closure of Gerstner + two-way normal nodes is retained.
#ifndef OV_UBER_GRAPH_PRIMITIVES_V03_INCLUDED
#define OV_UBER_GRAPH_PRIMITIVES_V03_INCLUDED
void Unity_Normalize_float3(float3 In, out float3 Out)
        {
            Out = normalize(In);
        }

void Unity_Divide_float(float A, float B, out float Out)
        {
            Out = A / B;
        }

void Unity_Multiply_float3_float3(float3 A, float3 B, out float3 Out)
        {
        Out = A * B;
        }

void Unity_DotProduct_float3(float3 A, float3 B, out float Out)
        {
            Out = dot(A, B);
        }

void Unity_Multiply_float_float(float A, float B, out float Out)
        {
        Out = A * B;
        }

void Unity_SquareRoot_float(float In, out float Out)
        {
            Out = sqrt(In);
        }

void Unity_Subtract_float(float A, float B, out float Out)
        {
            Out = A - B;
        }

void Unity_Cosine_float(float In, out float Out)
        {
            Out = cos(In);
        }

void Unity_Sine_float(float In, out float Out)
        {
            Out = sin(In);
        }

void Unity_Subtract_float3(float3 A, float3 B, out float3 Out)
        {
            Out = A - B;
        }

void Unity_OneMinus_float(float In, out float Out)
        {
            Out = 1 - In;
        }

void Unity_Combine_float(float R, float G, float B, float A, out float4 RGBA, out float3 RGB, out float2 RG)
        {
            RGBA = float4(R, G, B, A);
            RGB = float3(R, G, B);
            RG = float2(R, G);
        }

struct Bindings_GersterWaveGenerator_aac6f1504e8ae554dac04c1d18eb799b_float
        {
        float3 WorldSpacePosition;
        float3 TimeParameters;
        };

void SG_GersterWaveGenerator_aac6f1504e8ae554dac04c1d18eb799b_float(float _WaveLength, float _WaveSharpness, float _WaveHeight, float _WaveSpeed, float3 _WaveDirection, Bindings_GersterWaveGenerator_aac6f1504e8ae554dac04c1d18eb799b_float IN, out float3 Displacement_2, out float3 Normal_1)
        {
        float3 _Property_c22f6ab07a7f41e8a08f475787b264cd_Out_0_Vector3 = _WaveDirection;
        float3 _Normalize_e84ca742aa8944978826c9515bc32a56_Out_1_Vector3;
        Unity_Normalize_float3(_Property_c22f6ab07a7f41e8a08f475787b264cd_Out_0_Vector3, _Normalize_e84ca742aa8944978826c9515bc32a56_Out_1_Vector3);
        float Constant_68bd9a24898a4b0f9b980e981fc6bcc2 = 6.283185;
        float _Property_aa28fe375b3140ed8f80aba471b0d2a2_Out_0_Float = _WaveLength;
        float _Divide_ff1efa70309342bdbc68f6dd74c571a0_Out_2_Float;
        Unity_Divide_float(Constant_68bd9a24898a4b0f9b980e981fc6bcc2, _Property_aa28fe375b3140ed8f80aba471b0d2a2_Out_0_Float, _Divide_ff1efa70309342bdbc68f6dd74c571a0_Out_2_Float);
        float3 _Multiply_08b98c772ac64be58ce2eaec23c47615_Out_2_Vector3;
        Unity_Multiply_float3_float3(_Normalize_e84ca742aa8944978826c9515bc32a56_Out_1_Vector3, (_Divide_ff1efa70309342bdbc68f6dd74c571a0_Out_2_Float.xxx), _Multiply_08b98c772ac64be58ce2eaec23c47615_Out_2_Vector3);
        float _DotProduct_99d700641fd24b33b655562f3431cbfb_Out_2_Float;
        Unity_DotProduct_float3(IN.WorldSpacePosition, _Multiply_08b98c772ac64be58ce2eaec23c47615_Out_2_Vector3, _DotProduct_99d700641fd24b33b655562f3431cbfb_Out_2_Float);
        float _Multiply_6f33655d44944619bfab949ebef93873_Out_2_Float;
        Unity_Multiply_float_float(_Divide_ff1efa70309342bdbc68f6dd74c571a0_Out_2_Float, 9.8, _Multiply_6f33655d44944619bfab949ebef93873_Out_2_Float);
        float _SquareRoot_031ed07515f44c8da23b44827ea2e05d_Out_1_Float;
        Unity_SquareRoot_float(_Multiply_6f33655d44944619bfab949ebef93873_Out_2_Float, _SquareRoot_031ed07515f44c8da23b44827ea2e05d_Out_1_Float);
        float _Property_0b28b6176153414fab597237a3fb905f_Out_0_Float = _WaveSpeed;
        float _Multiply_28c33512375341dd9555eb1651ac7b94_Out_2_Float;
        Unity_Multiply_float_float(IN.TimeParameters.x, _Property_0b28b6176153414fab597237a3fb905f_Out_0_Float, _Multiply_28c33512375341dd9555eb1651ac7b94_Out_2_Float);
        float _Multiply_0b59a8ba36f045e8ab025e073a4a993e_Out_2_Float;
        Unity_Multiply_float_float(_SquareRoot_031ed07515f44c8da23b44827ea2e05d_Out_1_Float, _Multiply_28c33512375341dd9555eb1651ac7b94_Out_2_Float, _Multiply_0b59a8ba36f045e8ab025e073a4a993e_Out_2_Float);
        float _Subtract_dd4f202b4d91418f802f23b9a0f6da4c_Out_2_Float;
        Unity_Subtract_float(_DotProduct_99d700641fd24b33b655562f3431cbfb_Out_2_Float, _Multiply_0b59a8ba36f045e8ab025e073a4a993e_Out_2_Float, _Subtract_dd4f202b4d91418f802f23b9a0f6da4c_Out_2_Float);
        float _Cosine_7f3e2eba8d2346609824dbc2a7b8597c_Out_1_Float;
        Unity_Cosine_float(_Subtract_dd4f202b4d91418f802f23b9a0f6da4c_Out_2_Float, _Cosine_7f3e2eba8d2346609824dbc2a7b8597c_Out_1_Float);
        float3 _Vector3_363670f03b854bbb86697500817d7c49_Out_0_Vector3 = float3(float(0), float(1), float(0));
        float3 _Multiply_897bbe42bfbd4acd947ad422bc7c0d7e_Out_2_Vector3;
        Unity_Multiply_float3_float3((_Cosine_7f3e2eba8d2346609824dbc2a7b8597c_Out_1_Float.xxx), _Vector3_363670f03b854bbb86697500817d7c49_Out_0_Vector3, _Multiply_897bbe42bfbd4acd947ad422bc7c0d7e_Out_2_Vector3);
        float _Property_252ad527f2db4c82bd221e708f1c7640_Out_0_Float = _WaveHeight;
        float3 _Multiply_48312e714b294808b634c3e418eb01e0_Out_2_Vector3;
        Unity_Multiply_float3_float3(_Multiply_897bbe42bfbd4acd947ad422bc7c0d7e_Out_2_Vector3, (_Property_252ad527f2db4c82bd221e708f1c7640_Out_0_Float.xxx), _Multiply_48312e714b294808b634c3e418eb01e0_Out_2_Vector3);
        float _Sine_b45a476fd79e429b8ec55916227c39d1_Out_1_Float;
        Unity_Sine_float(_Subtract_dd4f202b4d91418f802f23b9a0f6da4c_Out_2_Float, _Sine_b45a476fd79e429b8ec55916227c39d1_Out_1_Float);
        float _Property_447e259f03c94d6c94db12f8218ab335_Out_0_Float = _WaveSharpness;
        float _Property_b461575898c74138900cb98af14a0696_Out_0_Float = _WaveHeight;
        float _Multiply_adbf1599197848f795f04d0529ce80b2_Out_2_Float;
        Unity_Multiply_float_float(_Divide_ff1efa70309342bdbc68f6dd74c571a0_Out_2_Float, _Property_b461575898c74138900cb98af14a0696_Out_0_Float, _Multiply_adbf1599197848f795f04d0529ce80b2_Out_2_Float);
        float _Divide_325b7ee2dd424c2697f1ba7c9aaee097_Out_2_Float;
        Unity_Divide_float(_Property_447e259f03c94d6c94db12f8218ab335_Out_0_Float, _Multiply_adbf1599197848f795f04d0529ce80b2_Out_2_Float, _Divide_325b7ee2dd424c2697f1ba7c9aaee097_Out_2_Float);
        float _Multiply_c4ebd9f054154d9b90f6a6c2a30fc6f1_Out_2_Float;
        Unity_Multiply_float_float(_Divide_325b7ee2dd424c2697f1ba7c9aaee097_Out_2_Float, _Property_b461575898c74138900cb98af14a0696_Out_0_Float, _Multiply_c4ebd9f054154d9b90f6a6c2a30fc6f1_Out_2_Float);
        float _Multiply_9c2537f9955d42e1b55040cf14172437_Out_2_Float;
        Unity_Multiply_float_float(_Sine_b45a476fd79e429b8ec55916227c39d1_Out_1_Float, _Multiply_c4ebd9f054154d9b90f6a6c2a30fc6f1_Out_2_Float, _Multiply_9c2537f9955d42e1b55040cf14172437_Out_2_Float);
        float3 _Multiply_0afaa06b717a433ab9fdf9e6f909c7f1_Out_2_Vector3;
        Unity_Multiply_float3_float3(_Normalize_e84ca742aa8944978826c9515bc32a56_Out_1_Vector3, (_Multiply_9c2537f9955d42e1b55040cf14172437_Out_2_Float.xxx), _Multiply_0afaa06b717a433ab9fdf9e6f909c7f1_Out_2_Vector3);
        float3 _Subtract_d6656e1dfbcf4293bd08ed14b00fee23_Out_2_Vector3;
        Unity_Subtract_float3(_Multiply_48312e714b294808b634c3e418eb01e0_Out_2_Vector3, _Multiply_0afaa06b717a433ab9fdf9e6f909c7f1_Out_2_Vector3, _Subtract_d6656e1dfbcf4293bd08ed14b00fee23_Out_2_Vector3);
        float _Multiply_b538ab63330c4a149c734f355b090396_Out_2_Float;
        Unity_Multiply_float_float(_Sine_b45a476fd79e429b8ec55916227c39d1_Out_1_Float, _Multiply_adbf1599197848f795f04d0529ce80b2_Out_2_Float, _Multiply_b538ab63330c4a149c734f355b090396_Out_2_Float);
        float3 _Multiply_ae32455b487545fbaee9c723965df5f8_Out_2_Vector3;
        Unity_Multiply_float3_float3((_Multiply_b538ab63330c4a149c734f355b090396_Out_2_Float.xxx), _Normalize_e84ca742aa8944978826c9515bc32a56_Out_1_Vector3, _Multiply_ae32455b487545fbaee9c723965df5f8_Out_2_Vector3);
        float _Split_b4fff87934d64190aff094d2d45e3cea_R_1_Float = _Multiply_ae32455b487545fbaee9c723965df5f8_Out_2_Vector3[0];
        float _Split_b4fff87934d64190aff094d2d45e3cea_G_2_Float = _Multiply_ae32455b487545fbaee9c723965df5f8_Out_2_Vector3[1];
        float _Split_b4fff87934d64190aff094d2d45e3cea_B_3_Float = _Multiply_ae32455b487545fbaee9c723965df5f8_Out_2_Vector3[2];
        float _Split_b4fff87934d64190aff094d2d45e3cea_A_4_Float = 0;
        float _Multiply_88f127ac902042338e65a6caf331633b_Out_2_Float;
        Unity_Multiply_float_float(_Cosine_7f3e2eba8d2346609824dbc2a7b8597c_Out_1_Float, _Multiply_adbf1599197848f795f04d0529ce80b2_Out_2_Float, _Multiply_88f127ac902042338e65a6caf331633b_Out_2_Float);
        float _Multiply_9640c067ebdd41bc905ace2b4b8249b5_Out_2_Float;
        Unity_Multiply_float_float(_Divide_325b7ee2dd424c2697f1ba7c9aaee097_Out_2_Float, _Multiply_88f127ac902042338e65a6caf331633b_Out_2_Float, _Multiply_9640c067ebdd41bc905ace2b4b8249b5_Out_2_Float);
        float _OneMinus_c9562aa601614b8f9392cd41ab7ee441_Out_1_Float;
        Unity_OneMinus_float(_Multiply_9640c067ebdd41bc905ace2b4b8249b5_Out_2_Float, _OneMinus_c9562aa601614b8f9392cd41ab7ee441_Out_1_Float);
        float4 _Combine_f9fbf09177cb4d9ab67cd2f6f3978c15_RGBA_4_Vector4;
        float3 _Combine_f9fbf09177cb4d9ab67cd2f6f3978c15_RGB_5_Vector3;
        float2 _Combine_f9fbf09177cb4d9ab67cd2f6f3978c15_RG_6_Vector2;
        Unity_Combine_float(_Split_b4fff87934d64190aff094d2d45e3cea_R_1_Float, _OneMinus_c9562aa601614b8f9392cd41ab7ee441_Out_1_Float, _Split_b4fff87934d64190aff094d2d45e3cea_B_3_Float, float(0), _Combine_f9fbf09177cb4d9ab67cd2f6f3978c15_RGBA_4_Vector4, _Combine_f9fbf09177cb4d9ab67cd2f6f3978c15_RGB_5_Vector3, _Combine_f9fbf09177cb4d9ab67cd2f6f3978c15_RG_6_Vector2);
        Displacement_2 = _Subtract_d6656e1dfbcf4293bd08ed14b00fee23_Out_2_Vector3;
        Normal_1 = _Combine_f9fbf09177cb4d9ab67cd2f6f3978c15_RGB_5_Vector3;
        }

void Unity_Multiply_float2_float2(float2 A, float2 B, out float2 Out)
        {
        Out = A * B;
        }

struct Bindings_WorldSpaceYProjectUV_3c92bbeda3ef09948aa60671fb1c5bf9_float
        {
        float3 AbsoluteWorldSpacePosition;
        };

void SG_WorldSpaceYProjectUV_3c92bbeda3ef09948aa60671fb1c5bf9_float(Bindings_WorldSpaceYProjectUV_3c92bbeda3ef09948aa60671fb1c5bf9_float IN, out float2 UV_1)
        {
        float _Split_aac80bd9d812460dbb181ce53c21f9ba_R_1_Float = IN.AbsoluteWorldSpacePosition[0];
        float _Split_aac80bd9d812460dbb181ce53c21f9ba_G_2_Float = IN.AbsoluteWorldSpacePosition[1];
        float _Split_aac80bd9d812460dbb181ce53c21f9ba_B_3_Float = IN.AbsoluteWorldSpacePosition[2];
        float _Split_aac80bd9d812460dbb181ce53c21f9ba_A_4_Float = 0;
        float2 _Vector2_c55bbc10935840089253ebf224a3f307_Out_0_Vector2 = float2(_Split_aac80bd9d812460dbb181ce53c21f9ba_R_1_Float, _Split_aac80bd9d812460dbb181ce53c21f9ba_B_3_Float);
        float _Float_a4cc86e3629b4ddcb7a524b92e6bfd47_Out_0_Float = float(0.1);
        float2 _Multiply_8ef444db46c64f3d90c30f2caafa1dbd_Out_2_Vector2;
        Unity_Multiply_float2_float2(_Vector2_c55bbc10935840089253ebf224a3f307_Out_0_Vector2, (_Float_a4cc86e3629b4ddcb7a524b92e6bfd47_Out_0_Float.xx), _Multiply_8ef444db46c64f3d90c30f2caafa1dbd_Out_2_Vector2);
        UV_1 = _Multiply_8ef444db46c64f3d90c30f2caafa1dbd_Out_2_Vector2;
        }

void Unity_TilingAndOffset_float(float2 UV, float2 Tiling, float2 Offset, out float2 Out)
        {
            Out = UV * Tiling + Offset;
        }

struct Bindings_UVPanner_c66b9ecf06c9a8141b68bc51420059db_float
        {
        float3 TimeParameters;
        };

void SG_UVPanner_c66b9ecf06c9a8141b68bc51420059db_float(float2 _UV, float2 _Speed, float2 _Tile, float _Scale, Bindings_UVPanner_c66b9ecf06c9a8141b68bc51420059db_float IN, out float2 UV_1)
        {
        float2 _Property_9c69efaa3ad348f5920432468f65b498_Out_0_Vector2 = _UV;
        float2 _Property_f1a62686e2bb46988bb0b7cdb6a92470_Out_0_Vector2 = _Tile;
        float _Property_34099c1d179042f3a1fb928ce818a216_Out_0_Float = _Scale;
        float2 _Multiply_a3abb5a6338f4d0aba3c64ead5fa01f7_Out_2_Vector2;
        Unity_Multiply_float2_float2(_Property_f1a62686e2bb46988bb0b7cdb6a92470_Out_0_Vector2, (_Property_34099c1d179042f3a1fb928ce818a216_Out_0_Float.xx), _Multiply_a3abb5a6338f4d0aba3c64ead5fa01f7_Out_2_Vector2);
        float2 _Property_ff5f4f42e6284552a3e750d09cc1c1e0_Out_0_Vector2 = _Speed;
        float _Float_4bad4b2e939a4c4b8843f18bc6ce3630_Out_0_Float = float(0.1);
        float2 _Multiply_7aba51a6d0cc41f6976dea86dcfcbda4_Out_2_Vector2;
        Unity_Multiply_float2_float2(_Property_ff5f4f42e6284552a3e750d09cc1c1e0_Out_0_Vector2, (_Float_4bad4b2e939a4c4b8843f18bc6ce3630_Out_0_Float.xx), _Multiply_7aba51a6d0cc41f6976dea86dcfcbda4_Out_2_Vector2);
        float2 _Multiply_6d8663918ae34d0d97bab66ab7106797_Out_2_Vector2;
        Unity_Multiply_float2_float2(_Multiply_7aba51a6d0cc41f6976dea86dcfcbda4_Out_2_Vector2, (IN.TimeParameters.x.xx), _Multiply_6d8663918ae34d0d97bab66ab7106797_Out_2_Vector2);
        float2 _TilingAndOffset_2e531f7e856d49fe999971f02cf6709c_Out_3_Vector2;
        Unity_TilingAndOffset_float(_Property_9c69efaa3ad348f5920432468f65b498_Out_0_Vector2, _Multiply_a3abb5a6338f4d0aba3c64ead5fa01f7_Out_2_Vector2, _Multiply_6d8663918ae34d0d97bab66ab7106797_Out_2_Vector2, _TilingAndOffset_2e531f7e856d49fe999971f02cf6709c_Out_3_Vector2);
        UV_1 = _TilingAndOffset_2e531f7e856d49fe999971f02cf6709c_Out_3_Vector2;
        }

void Unity_Lerp_float4(float4 A, float4 B, float4 T, out float4 Out)
        {
            Out = lerp(A, B, T);
        }

void Unity_Lerp_float(float A, float B, float T, out float Out)
        {
            Out = lerp(A, B, T);
        }

void Unity_NormalStrength_float(float3 In, float Strength, out float3 Out)
        {
            Out = float3(In.rg * Strength, lerp(1, In.b, saturate(Strength)));
        }

struct Bindings_var2WayNormalBlend_0731d7b977697114da66cb4d58f833a0_float
        {
        float3 AbsoluteWorldSpacePosition;
        float3 TimeParameters;
        };

void SG_var2WayNormalBlend_0731d7b977697114da66cb4d58f833a0_float(float _Distance_Mask, float _NormalStrength, float _DistancelStrength, UnityTexture2D _NormalMap, float _NormalPan, float _NormalTile, Bindings_var2WayNormalBlend_0731d7b977697114da66cb4d58f833a0_float IN, out float3 Unscaled_Normal_1, out float3 Normal_2)
        {
        UnityTexture2D _Property_2d9e5a6d4b8343ffbf99f3e37cb657fb_Out_0_Texture2D = _NormalMap;
        Bindings_WorldSpaceYProjectUV_3c92bbeda3ef09948aa60671fb1c5bf9_float _WorldSpaceYProjectUV_a0c6e3e9a06842a6bba606e4fbee1e2b;
        _WorldSpaceYProjectUV_a0c6e3e9a06842a6bba606e4fbee1e2b.AbsoluteWorldSpacePosition = IN.AbsoluteWorldSpacePosition;
        float2 _WorldSpaceYProjectUV_a0c6e3e9a06842a6bba606e4fbee1e2b_UV_1_Vector2;
        SG_WorldSpaceYProjectUV_3c92bbeda3ef09948aa60671fb1c5bf9_float(_WorldSpaceYProjectUV_a0c6e3e9a06842a6bba606e4fbee1e2b, _WorldSpaceYProjectUV_a0c6e3e9a06842a6bba606e4fbee1e2b_UV_1_Vector2);
        float _Property_b4e1fe5be9124ec8ba5fbe43493c0144_Out_0_Float = _NormalPan;
        float _Multiply_a1c6dacee293488bae983cabf8dad799_Out_2_Float;
        Unity_Multiply_float_float(_Property_b4e1fe5be9124ec8ba5fbe43493c0144_Out_0_Float, -0.5, _Multiply_a1c6dacee293488bae983cabf8dad799_Out_2_Float);
        float _Property_7743511e58d54bdea2452a861f87cca9_Out_0_Float = _NormalTile;
        float _Multiply_d3ad8a04204e4a0c898ff5dda97c58f2_Out_2_Float;
        Unity_Multiply_float_float(_Property_7743511e58d54bdea2452a861f87cca9_Out_0_Float, 0.5, _Multiply_d3ad8a04204e4a0c898ff5dda97c58f2_Out_2_Float);
        Bindings_UVPanner_c66b9ecf06c9a8141b68bc51420059db_float _UVPanner_84663611f3954191b88c8e69ca60949c;
        _UVPanner_84663611f3954191b88c8e69ca60949c.TimeParameters = IN.TimeParameters;
        float2 _UVPanner_84663611f3954191b88c8e69ca60949c_UV_1_Vector2;
        SG_UVPanner_c66b9ecf06c9a8141b68bc51420059db_float(_WorldSpaceYProjectUV_a0c6e3e9a06842a6bba606e4fbee1e2b_UV_1_Vector2, (_Multiply_a1c6dacee293488bae983cabf8dad799_Out_2_Float.xx), (_Multiply_d3ad8a04204e4a0c898ff5dda97c58f2_Out_2_Float.xx), half(1), _UVPanner_84663611f3954191b88c8e69ca60949c, _UVPanner_84663611f3954191b88c8e69ca60949c_UV_1_Vector2);
        float4 _SampleTexture2D_616c09880f5d440fa8df7242be9308a7_RGBA_0_Vector4 = SAMPLE_TEXTURE2D(_Property_2d9e5a6d4b8343ffbf99f3e37cb657fb_Out_0_Texture2D.tex, _Property_2d9e5a6d4b8343ffbf99f3e37cb657fb_Out_0_Texture2D.samplerstate, _Property_2d9e5a6d4b8343ffbf99f3e37cb657fb_Out_0_Texture2D.GetTransformedUV(_UVPanner_84663611f3954191b88c8e69ca60949c_UV_1_Vector2) );
        if (_Property_2d9e5a6d4b8343ffbf99f3e37cb657fb_Out_0_Texture2D.hdrDecode.x > 0)
        _SampleTexture2D_616c09880f5d440fa8df7242be9308a7_RGBA_0_Vector4 = DecodeHDRSample(_SampleTexture2D_616c09880f5d440fa8df7242be9308a7_RGBA_0_Vector4, _Property_2d9e5a6d4b8343ffbf99f3e37cb657fb_Out_0_Texture2D.hdrDecode);
        _SampleTexture2D_616c09880f5d440fa8df7242be9308a7_RGBA_0_Vector4.rgb = UnpackNormal(_SampleTexture2D_616c09880f5d440fa8df7242be9308a7_RGBA_0_Vector4);
        float _SampleTexture2D_616c09880f5d440fa8df7242be9308a7_R_4_Float = _SampleTexture2D_616c09880f5d440fa8df7242be9308a7_RGBA_0_Vector4.r;
        float _SampleTexture2D_616c09880f5d440fa8df7242be9308a7_G_5_Float = _SampleTexture2D_616c09880f5d440fa8df7242be9308a7_RGBA_0_Vector4.g;
        float _SampleTexture2D_616c09880f5d440fa8df7242be9308a7_B_6_Float = _SampleTexture2D_616c09880f5d440fa8df7242be9308a7_RGBA_0_Vector4.b;
        float _SampleTexture2D_616c09880f5d440fa8df7242be9308a7_A_7_Float = _SampleTexture2D_616c09880f5d440fa8df7242be9308a7_RGBA_0_Vector4.a;
        UnityTexture2D _Property_c58d82e0e7f7418aa2e15912be0b84c8_Out_0_Texture2D = _NormalMap;
        float _Property_26c1d3d4d06842de895ec288e67a0f87_Out_0_Float = _NormalPan;
        float _Property_d69e9c4f8cab461ba3ab7a13d782b332_Out_0_Float = _NormalTile;
        Bindings_UVPanner_c66b9ecf06c9a8141b68bc51420059db_float _UVPanner_f7c34f769a574f21b30398fad3a50617;
        _UVPanner_f7c34f769a574f21b30398fad3a50617.TimeParameters = IN.TimeParameters;
        float2 _UVPanner_f7c34f769a574f21b30398fad3a50617_UV_1_Vector2;
        SG_UVPanner_c66b9ecf06c9a8141b68bc51420059db_float(_WorldSpaceYProjectUV_a0c6e3e9a06842a6bba606e4fbee1e2b_UV_1_Vector2, (_Property_26c1d3d4d06842de895ec288e67a0f87_Out_0_Float.xx), (_Property_d69e9c4f8cab461ba3ab7a13d782b332_Out_0_Float.xx), half(1), _UVPanner_f7c34f769a574f21b30398fad3a50617, _UVPanner_f7c34f769a574f21b30398fad3a50617_UV_1_Vector2);
        float4 _SampleTexture2D_8311c849bc5d433497f9b50c92e24569_RGBA_0_Vector4 = SAMPLE_TEXTURE2D(_Property_c58d82e0e7f7418aa2e15912be0b84c8_Out_0_Texture2D.tex, _Property_c58d82e0e7f7418aa2e15912be0b84c8_Out_0_Texture2D.samplerstate, _Property_c58d82e0e7f7418aa2e15912be0b84c8_Out_0_Texture2D.GetTransformedUV(_UVPanner_f7c34f769a574f21b30398fad3a50617_UV_1_Vector2) );
        if (_Property_c58d82e0e7f7418aa2e15912be0b84c8_Out_0_Texture2D.hdrDecode.x > 0)
        _SampleTexture2D_8311c849bc5d433497f9b50c92e24569_RGBA_0_Vector4 = DecodeHDRSample(_SampleTexture2D_8311c849bc5d433497f9b50c92e24569_RGBA_0_Vector4, _Property_c58d82e0e7f7418aa2e15912be0b84c8_Out_0_Texture2D.hdrDecode);
        _SampleTexture2D_8311c849bc5d433497f9b50c92e24569_RGBA_0_Vector4.rgb = UnpackNormal(_SampleTexture2D_8311c849bc5d433497f9b50c92e24569_RGBA_0_Vector4);
        float _SampleTexture2D_8311c849bc5d433497f9b50c92e24569_R_4_Float = _SampleTexture2D_8311c849bc5d433497f9b50c92e24569_RGBA_0_Vector4.r;
        float _SampleTexture2D_8311c849bc5d433497f9b50c92e24569_G_5_Float = _SampleTexture2D_8311c849bc5d433497f9b50c92e24569_RGBA_0_Vector4.g;
        float _SampleTexture2D_8311c849bc5d433497f9b50c92e24569_B_6_Float = _SampleTexture2D_8311c849bc5d433497f9b50c92e24569_RGBA_0_Vector4.b;
        float _SampleTexture2D_8311c849bc5d433497f9b50c92e24569_A_7_Float = _SampleTexture2D_8311c849bc5d433497f9b50c92e24569_RGBA_0_Vector4.a;
        float _Float_b334fa102a0f4893908e3de0a464be3a_Out_0_Float = float(0.5);
        float4 _Lerp_c39fc1ff3bfc4a11aec472dbdec68e88_Out_3_Vector4;
        Unity_Lerp_float4(_SampleTexture2D_616c09880f5d440fa8df7242be9308a7_RGBA_0_Vector4, _SampleTexture2D_8311c849bc5d433497f9b50c92e24569_RGBA_0_Vector4, (_Float_b334fa102a0f4893908e3de0a464be3a_Out_0_Float.xxxx), _Lerp_c39fc1ff3bfc4a11aec472dbdec68e88_Out_3_Vector4);
        float _Property_720434c5dc974c6d9f0808728aab2123_Out_0_Float = _NormalStrength;
        float _Property_214273a19f0a4c5eb1100de73bfee2dc_Out_0_Float = _DistancelStrength;
        float _Property_31974a62287f4f3787a03f2b490ab43b_Out_0_Float = _Distance_Mask;
        float _Lerp_a45754d7929a4f2688f6d936e0ff28e7_Out_3_Float;
        Unity_Lerp_float(_Property_720434c5dc974c6d9f0808728aab2123_Out_0_Float, _Property_214273a19f0a4c5eb1100de73bfee2dc_Out_0_Float, _Property_31974a62287f4f3787a03f2b490ab43b_Out_0_Float, _Lerp_a45754d7929a4f2688f6d936e0ff28e7_Out_3_Float);
        float3 _NormalStrength_2a6cbafbd7144b17942e08f1730c3784_Out_2_Vector3;
        Unity_NormalStrength_float((_Lerp_c39fc1ff3bfc4a11aec472dbdec68e88_Out_3_Vector4.xyz), _Lerp_a45754d7929a4f2688f6d936e0ff28e7_Out_3_Float, _NormalStrength_2a6cbafbd7144b17942e08f1730c3784_Out_2_Vector3);
        Unscaled_Normal_1 = (_Lerp_c39fc1ff3bfc4a11aec472dbdec68e88_Out_3_Vector4.xyz);
        Normal_2 = _NormalStrength_2a6cbafbd7144b17942e08f1730c3784_Out_2_Vector3;
        }
#endif
